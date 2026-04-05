def test_import_evaluate_condition_step():
    from backend.services.automation_step_executors import condition as cond_executor

    assert hasattr(cond_executor, "evaluate_condition_step")
