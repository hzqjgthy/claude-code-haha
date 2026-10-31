from claude_code_py.providers.remote import StatefulRemoteProvider


def test_stateful_remote_provider_persists_lifecycle(tmp_path) -> None:
    path = tmp_path / "remote_state.json"
    provider = StatefulRemoteProvider(path)

    status = provider.connect_direct(
        session_url="ws://127.0.0.1:9000/session/demo",
        local_session_id="sess-local",
        remote_session_id="remote-1",
    )
    assert status.mode == "direct_connect"
    assert status.connected is True

    heartbeat = provider.heartbeat()
    assert heartbeat.last_heartbeat_at is not None

    archived = provider.archive()
    assert archived is not None
    assert archived.remote_session_id == "remote-1"

    restored = StatefulRemoteProvider(path)
    assert restored.status().mode == "local"
    history = restored.archived_sessions()
    assert len(history) == 1
    assert history[0].remote_session_id == "remote-1"


def test_stateful_remote_provider_supports_hydrated_remote_state(tmp_path) -> None:
    provider = StatefulRemoteProvider(tmp_path / "remote_state.json")

    status = provider.hydrate(
        local_session_id="sess-local",
        remote_session_id="remote-2",
        session_url="https://example.com/session/remote-2",
        hydrated_from="/tmp/share.json",
        detail="Hydrated remote transcript bundle",
    )

    assert status.mode == "bridge"
    assert status.connected is False
    assert status.hydrated_from == "/tmp/share.json"
    assert status.can_reconnect is True

    reconnected = provider.reconnect()
    assert reconnected.connected is True


def test_stateful_remote_provider_tracks_ssh_mode(tmp_path) -> None:
    provider = StatefulRemoteProvider(tmp_path / "remote_state.json")

    status = provider.connect_ssh(
        host="demo-host",
        local_session_id="sess-local",
        remote_cwd="/srv/app",
    )

    assert status.mode == "ssh"
    assert status.transport == "ssh"
    assert status.session_url == "ssh://demo-host"
