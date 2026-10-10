from ai_core import ErrorCategory, EvalStatus, ExperimentStatus, RunStatus


def test_status_values_cover_spec():
    assert RunStatus.COMPLETED == "completed"
    assert RunStatus.AGENT_ERROR == "agent_error"
    assert RunStatus.TIMEOUT == "timeout"
    assert RunStatus.INTERRUPTED == "interrupted"
    assert RunStatus.SETUP_ERROR == "setup_error"
    assert RunStatus.EVALUATION_ERROR == "evaluation_error"
    assert RunStatus.CANCELLED == "cancelled"

    assert EvalStatus.PASS == "pass"  # noqa: S105 - status literal, not a password
    assert EvalStatus.FAIL == "fail"
    assert EvalStatus.EVALUATION_ERROR == "evaluation_error"
    assert EvalStatus.NOT_EVALUATED == "not_evaluated"

    assert ExperimentStatus.COMPLETED == "completed"
    assert ExperimentStatus.COMPLETED_PARTIAL == "completed_partial"

    assert ErrorCategory.TIMEOUT == "timeout"


def test_status_importable_from_core():
    import ai_core

    assert ai_core.RunStatus is RunStatus
