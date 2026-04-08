def test_import_execute_llm_chat_step():
    from backend.services.automation_step_executors import llm_chat as llm_executor

    assert hasattr(llm_executor, "execute_llm_chat_step")
