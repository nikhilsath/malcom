def test_tool_executor_importable():
    from backend.services.automation_step_executors.tool import execute_tool_step

    assert callable(execute_tool_step)
