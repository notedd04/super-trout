from clouddeck.database import Database


def test_database_persists_settings_and_events(tmp_path):
    db = Database(tmp_path / "clouddeck.sqlite3")
    assert db.get_setting("profile") == "balanced"
    db.set_setting("profile", "data_saver")
    db.event("profile.changed", {"profile": "data_saver"})
    assert db.get_setting("profile") == "data_saver"
    events = db.recent_events(5)
    assert len(events) == 1
    assert events[0]["type"] == "profile.changed"
    assert events[0]["detail"]["profile"] == "data_saver"


def test_session_lifecycle_is_auditable(tmp_path):
    db = Database(tmp_path / "clouddeck.sqlite3")
    session_id = db.session_started("balanced")
    assert db.active_session_id() == session_id
    db.session_stopped(session_id)
    assert db.active_session_id() is None


def test_event_history_is_capped_to_the_latest_records(tmp_path, monkeypatch):
    db = Database(tmp_path / "clouddeck.sqlite3")
    monkeypatch.setattr(Database, "MAX_EVENTS", 3)
    for value in range(5):
        db.event("test.event", {"value": value})

    events = db.recent_events(10)
    assert [event["detail"]["value"] for event in events] == [4, 3, 2]
