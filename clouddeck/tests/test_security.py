from clouddeck.security import SessionSecurity, hash_password, verify_password


def test_password_hash_round_trip_and_salt_uniqueness():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_signed_session_rejects_tampering():
    import base64
    secret = base64.urlsafe_b64encode(b"A" * 32).decode("ascii")
    security = SessionSecurity(secret)
    token, csrf, _expires = security.issue()
    decoded = security.decode(token)
    assert decoded is not None
    assert decoded[0] == csrf
    assert security.decode(token + "x") is None


def test_signed_session_rejects_expired_token(monkeypatch):
    import base64
    import clouddeck.security as module
    secret = base64.urlsafe_b64encode(b"B" * 32).decode("ascii")
    security = SessionSecurity(secret)
    token, _csrf, _expires = security.issue()
    monkeypatch.setattr(module.time, "time", lambda: 4_000_000_000)
    assert security.decode(token) is None
