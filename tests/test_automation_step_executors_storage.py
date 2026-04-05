def test_import_execute_storage_step():
    from backend.services.automation_step_executors import storage as storage_executor

    assert hasattr(storage_executor, "execute_storage_step")
