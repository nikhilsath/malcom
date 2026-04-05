def test_import_execute_script_step_wrapper():
    from backend.services.automation_step_executors import script as script_executor

    assert hasattr(script_executor, "execute_script_step_wrapper")
