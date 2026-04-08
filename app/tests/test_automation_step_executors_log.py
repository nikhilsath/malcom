def test_log_executor_importable():
    from backend.services.automation_step_executors.log import execute_log_step

    assert callable(execute_log_step)
