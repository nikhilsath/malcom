from backend.services import connector_protection


def test_protect_unprotect_roundtrip():
    secret = "s3cr3t-value"
    protection_key = "test-key"
    token = connector_protection.protect_connector_secret_value(secret, protection_key)
    assert isinstance(token, str)
    restored = connector_protection.unprotect_connector_secret_value(token, protection_key)
    assert restored == secret
