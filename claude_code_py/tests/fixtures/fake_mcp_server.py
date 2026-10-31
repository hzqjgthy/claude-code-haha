import json
import sys


def read_message() -> dict[str, object] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("utf-8", errors="replace").strip()
        if not decoded:
            continue
        key, _, value = decoded.partition(":")
        headers[key.lower()] = value.strip()
    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        return None
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def write_message(payload: dict[str, object]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(
        f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body,
    )
    sys.stdout.buffer.flush()


def main() -> int:
    while True:
        message = read_message()
        if message is None:
            return 0
        method = message.get("method")
        if method == "initialize":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "protocolVersion": message.get("params", {}).get("protocolVersion"),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fake-mcp", "version": "0.1.0"},
                    },
                },
            )
            continue
        if method == "notifications/initialized":
            continue
        if method == "tools/list":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "echo_tool",
                                "description": "Echo MCP input",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                    },
                                    "required": ["text"],
                                },
                            }
                        ]
                    },
                },
            )
            continue
        if method == "tools/call":
            params = message.get("params", {})
            arguments = params.get("arguments", {}) if isinstance(params, dict) else {}
            text = arguments.get("text", "") if isinstance(arguments, dict) else ""
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"mcp-echo:{text}",
                            }
                        ],
                        "isError": False,
                    },
                },
            )
            continue
        write_message(
            {
                "jsonrpc": "2.0",
                "id": message["id"],
                "error": {"message": f"Unknown method: {method}"},
            },
        )


if __name__ == "__main__":
    raise SystemExit(main())
