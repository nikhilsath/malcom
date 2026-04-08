def test_connector_revoker_and_tester_importable():
    from backend.services.connector_revoker import revoke_connector_record
    from backend.services.connector_tester import test_connector_record

    assert callable(revoke_connector_record)
    assert callable(test_connector_record)
