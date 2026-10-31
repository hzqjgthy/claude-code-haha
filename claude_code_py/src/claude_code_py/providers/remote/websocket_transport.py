from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
from dataclasses import dataclass, field
from urllib.parse import urlparse


_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketTransportError(RuntimeError):
    pass


@dataclass(slots=True)
class WebSocketTextStream:
    sock: socket.socket
    client_side: bool
    _buffer: bytearray = field(default_factory=bytearray)
    _closed: bool = False

    def send_text(self, text: str) -> None:
        if self._closed:
            raise WebSocketTransportError("WebSocket stream is closed.")
        payload = text.encode("utf-8")
        frame = _build_frame(
            opcode=0x1,
            payload=payload,
            masked=self.client_side,
        )
        self.sock.sendall(frame)

    def recv_text(self) -> str | None:
        while not self._closed:
            opcode, payload = self._read_frame()
            if opcode == 0x1:
                return payload.decode("utf-8")
            if opcode == 0x8:
                self.close()
                return None
            if opcode == 0x9:
                self._send_control(opcode=0xA, payload=payload)
                continue
            if opcode == 0xA:
                continue
            raise WebSocketTransportError(f"Unsupported WebSocket opcode: {opcode}")
        return None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.sock.sendall(
                _build_frame(opcode=0x8, payload=b"", masked=self.client_side)
            )
        except OSError:
            pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()

    def _send_control(self, *, opcode: int, payload: bytes) -> None:
        if self._closed:
            return
        self.sock.sendall(
            _build_frame(opcode=opcode, payload=payload, masked=self.client_side)
        )

    def _read_frame(self) -> tuple[int, bytes]:
        header = self._read_exact(2)
        b1, b2 = header[0], header[1]
        fin = bool(b1 & 0x80)
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F

        if not fin:
            raise WebSocketTransportError("Fragmented WebSocket frames are not supported.")

        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]

        mask_key = self._read_exact(4) if masked else None
        payload = self._read_exact(length)
        if mask_key is not None:
            payload = bytes(
                value ^ mask_key[index % 4]
                for index, value in enumerate(payload)
            )
        return opcode, payload

    def _read_exact(self, size: int) -> bytes:
        while len(self._buffer) < size:
            chunk = self.sock.recv(max(4096, size - len(self._buffer)))
            if not chunk:
                self._closed = True
                raise WebSocketTransportError("WebSocket connection closed unexpectedly.")
            self._buffer.extend(chunk)
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data


def connect_websocket(url: str, *, timeout: float = 10.0) -> WebSocketTextStream:
    parsed = urlparse(url)
    if parsed.scheme != "ws":
        raise WebSocketTransportError(
            f"Unsupported WebSocket URL scheme '{parsed.scheme}'. Only ws:// is supported."
        )
    if parsed.hostname is None:
        raise WebSocketTransportError(f"Invalid WebSocket URL: {url}")

    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    sock = socket.create_connection((parsed.hostname, port), timeout=timeout)
    sock.settimeout(timeout)

    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request_lines = [
        f"GET {path} HTTP/1.1",
        f"Host: {parsed.hostname}:{port}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
        "",
        "",
    ]
    sock.sendall("\r\n".join(request_lines).encode("ascii"))
    status_line, headers, leftover = _read_http_headers(sock)
    if "101" not in status_line:
        sock.close()
        raise WebSocketTransportError(
            f"WebSocket upgrade failed: {status_line.strip() or 'missing status'}"
        )

    expected = base64.b64encode(
        hashlib.sha1(f"{key}{_WEBSOCKET_GUID}".encode("ascii")).digest()
    ).decode("ascii")
    if headers.get("sec-websocket-accept") != expected:
        sock.close()
        raise WebSocketTransportError("WebSocket handshake validation failed.")

    stream = WebSocketTextStream(sock=sock, client_side=True)
    if leftover:
        stream._buffer.extend(leftover)
    return stream


def accept_websocket_connection(
    conn: socket.socket,
    *,
    timeout: float = 30.0,
) -> WebSocketTextStream:
    conn.settimeout(timeout)
    status_line, headers, _ = _read_http_headers(conn)
    if not status_line.startswith("GET "):
        conn.close()
        raise WebSocketTransportError("WebSocket server received a non-GET request.")

    key = headers.get("sec-websocket-key")
    if not key:
        conn.close()
        raise WebSocketTransportError("Missing Sec-WebSocket-Key header.")

    accept = base64.b64encode(
        hashlib.sha1(f"{key}{_WEBSOCKET_GUID}".encode("ascii")).digest()
    ).decode("ascii")
    response = "\r\n".join(
        [
            "HTTP/1.1 101 Switching Protocols",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Accept: {accept}",
            "",
            "",
        ]
    )
    conn.sendall(response.encode("ascii"))
    return WebSocketTextStream(sock=conn, client_side=False)


def _read_http_headers(
    sock: socket.socket,
) -> tuple[str, dict[str, str], bytes]:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise WebSocketTransportError("Socket closed during WebSocket handshake.")
        data.extend(chunk)
    raw_headers, leftover = bytes(data).split(b"\r\n\r\n", 1)
    lines = raw_headers.decode("latin-1").split("\r\n")
    status_line = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return status_line, headers, leftover


def _build_frame(*, opcode: int, payload: bytes, masked: bool) -> bytes:
    header = bytearray([0x80 | opcode])
    payload_length = len(payload)
    mask_bit = 0x80 if masked else 0
    if payload_length < 126:
        header.append(mask_bit | payload_length)
    elif payload_length < (1 << 16):
        header.append(mask_bit | 126)
        header.extend(struct.pack("!H", payload_length))
    else:
        header.append(mask_bit | 127)
        header.extend(struct.pack("!Q", payload_length))

    if masked:
        mask_key = os.urandom(4)
        header.extend(mask_key)
        payload = bytes(
            value ^ mask_key[index % 4]
            for index, value in enumerate(payload)
        )
    return bytes(header) + payload
