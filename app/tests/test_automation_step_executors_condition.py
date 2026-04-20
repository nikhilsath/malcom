from types import SimpleNamespace

from backend.services.automation_step_executors.condition import evaluate_condition_step


def _build_condition_step(expression: str, *, stop_on_false: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id="condition-step",
        name="Check condition",
        config=SimpleNamespace(
            expression=expression,
            on_true_step_id="true-branch",
            on_false_step_id="false-branch",
            stop_on_false=stop_on_false,
        ),
    )


def test_evaluate_condition_step_returns_true_for_truthy_expression() -> None:
    result = evaluate_condition_step(
        None,
        None,
        step=_build_condition_step("1 < 2"),
        context={},
    )

    assert result.status == "completed"
    assert result.response_summary == "Condition matched."
    assert result.detail == {
        "expression": "1 < 2",
        "result": True,
        "stop_on_false": False,
    }
    assert result.output is True


def test_evaluate_condition_step_returns_false_for_falsy_expression() -> None:
    result = evaluate_condition_step(
        None,
        None,
        step=_build_condition_step("1 > 2"),
        context={},
    )

    assert result.status == "completed"
    assert result.response_summary == "Condition evaluated to false."
    assert result.detail == {
        "expression": "1 > 2",
        "result": False,
        "stop_on_false": False,
    }
    assert result.output is False
