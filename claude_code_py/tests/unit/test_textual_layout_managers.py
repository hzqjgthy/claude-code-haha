from claude_code_py.ui.layout import ModalManager, OverlayManager


def test_modal_manager_tracks_active_key() -> None:
    manager = ModalManager()

    assert manager.should_present("help") is True
    manager.mark_presented("help")
    assert manager.active_key == "help"
    assert manager.should_present("help") is False
    assert manager.should_present("policy") is True

    manager.clear()
    assert manager.active_key is None
    assert manager.should_present("help") is True


def test_overlay_manager_tracks_active_key() -> None:
    manager = OverlayManager()

    assert manager.should_present("req-1") is True
    manager.mark_presented("req-1")
    assert manager.active_key == "req-1"
    assert manager.should_present("req-1") is False
    assert manager.should_present("req-2") is True

    manager.clear()
    assert manager.active_key is None
