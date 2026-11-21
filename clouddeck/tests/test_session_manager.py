import time

import pytest

from clouddeck.services.session_manager import ALLOWED_KEYS, PROFILES, SessionManager


def test_profile_catalog_is_bounded_and_valid():
    assert set(PROFILES) == {"data_saver", "balanced", "portrait", "desktop"}
    assert PROFILES["balanced"]["resolution"] == "1024x576"
    assert PROFILES["portrait"]["resolution"] == "576x1024"
    assert PROFILES["data_saver"]["depth"] == 16


def test_pointer_is_bounded_and_reachable(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path)
    monkeypatch.setattr(manager, "status", lambda: {"running": True})
    monkeypatch.setattr("clouddeck.services.session_manager.shutil.which", lambda _name: "/usr/bin/xdotool")
    calls = []
    monkeypatch.setattr("clouddeck.services.session_manager.subprocess.run", lambda command, **kwargs: calls.append(command))

    assert manager.pointer(dx=700, dy=-700, button="left", scroll_y=30)["accepted"] is True
    assert calls[0] == ["xdotool", "mousemove_relative", "--", "500", "-500"]
    assert calls[-1] == ["xdotool", "click", "1"]
    manager.close()


def test_input_key_allowlist_rejects_untrusted_keys(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path)
    monkeypatch.setattr(manager, "status", lambda: {"running": True})
    monkeypatch.setattr("clouddeck.services.session_manager.shutil.which", lambda _name: "/usr/bin/xdotool")
    monkeypatch.setattr("clouddeck.services.session_manager.subprocess.run", lambda *args, **kwargs: None)
    with pytest.raises(ValueError):
        manager.set_keys(["w; rm -rf /"])
    assert "w" in ALLOWED_KEYS
    manager.close()


def test_input_key_diff_emits_press_and_release(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path)
    monkeypatch.setattr(manager, "status", lambda: {"running": True})
    monkeypatch.setattr("clouddeck.services.session_manager.shutil.which", lambda _name: "/usr/bin/xdotool")
    calls = []
    monkeypatch.setattr("clouddeck.services.session_manager.subprocess.run", lambda command, **kwargs: calls.append(command))
    first = manager.set_keys(["w", "space"])
    assert first["accepted"] is True
    assert set(manager.pressed_keys) == {"w", "space"}
    time.sleep(0.012)
    second = manager.set_keys([])
    assert second["accepted"] is True
    assert manager.pressed_keys == set()
    assert [call[:2] for call in calls] == [
        ["xdotool", "keydown"], ["xdotool", "keydown"],
        ["xdotool", "keyup"], ["xdotool", "keyup"],
    ]
    manager.close()


def test_desktop_status_is_false_without_process_records(tmp_path):
    manager = SessionManager(tmp_path)
    assert manager.status()["running"] is False
    manager.close()


def test_input_lease_watchdog_releases_keys_after_client_disappears(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path)
    monkeypatch.setattr("clouddeck.services.session_manager.shutil.which", lambda _name: "/usr/bin/xdotool")
    calls = []
    monkeypatch.setattr("clouddeck.services.session_manager.subprocess.run", lambda command, **kwargs: calls.append(command))
    manager.pressed_keys = {"w", "space"}
    manager._last_input_at = time.monotonic()

    expired = manager._expire_stale_keys(manager._last_input_at + manager.INPUT_LEASE_SECONDS + 0.01)

    assert expired is True
    assert manager.pressed_keys == set()
    assert [command[1] for command in calls] == ["keyup", "keyup"]
    manager.close()


def test_input_heartbeat_renews_only_an_active_key_lease(tmp_path):
    manager = SessionManager(tmp_path)
    manager.pressed_keys = {"w"}
    manager._last_input_at = time.monotonic() - 0.5
    before = manager._last_input_at
    result = manager.heartbeat()
    assert result["ok"] is True
    assert result["active"] is True
    assert result["lease_ms"] == 900
    assert manager._last_input_at >= before
    manager.close()


def test_pid_file_is_not_trusted_when_process_identity_does_not_match(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path)
    pid_file = manager.pid_dir / "xvfb.pid"
    pid_file.write_text(str(__import__("os").getpid()), encoding="utf-8")
    monkeypatch.setattr(manager, "_pid_alive", lambda _pid: True)

    assert manager._read_pid("xvfb") is None
    assert not pid_file.exists()
    manager.close()
