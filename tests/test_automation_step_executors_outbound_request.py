def test_outbound_request_executor_importable():
    from backend.services.automation_step_executors.outbound_request import execute_outbound_request_step

    assert callable(execute_outbound_request_step)
