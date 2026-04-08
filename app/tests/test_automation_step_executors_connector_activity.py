def test_import_execute_connector_activity_step():
    from backend.services.automation_step_executors import connector_activity as ca_executor

    assert hasattr(ca_executor, "execute_connector_activity_step")
