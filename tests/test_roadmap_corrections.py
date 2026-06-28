from app.pipeline.failed_query import CONTEXT_BLOCKED_AFTER_ERROR, FAILED_QUERY_ERROR, FAILED_QUERY_STATE
from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_semantics import apply_report_semantics
from app.reports.roadmap.compatibility import check_roadmap_compatibility
from app.reports.roadmap.corrections import build_failed_roadmap_correction, resolve_roadmap_recovery


def test_resolve_roadmap_recovery_detects_steps_word() -> None:
    result = resolve_roadmap_recovery("этапы")

    assert result is not None
    assert result[1]["view"] == "roadmap_steps"


def test_resolve_roadmap_recovery_does_not_treat_floor_as_step() -> None:
    result = resolve_roadmap_recovery("сколько этажей?")

    assert result is None


def test_failed_roadmap_metric_keeps_error_after_period_followup() -> None:
    state, parsed = build_failed_roadmap_correction(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "metric_not_supported_for_roadmap",
            FAILED_QUERY_STATE: {
                "report_type": "roadmap",
                "project": "all",
                "metrics": ["plan"],
                "view": None,
                "filters": {},
                "group_by": [],
            },
        },
        "апрель",
    )

    assert parsed is not None
    assert state["report_type"] == "roadmap"
    assert state["period"] == {"label": "апрель"}
    assert parsed.state_delta.period.label == "апрель"
    assert parsed.state_delta.metrics == ["plan"]


def test_roadmap_compatibility_rejects_plan_metric_from_frame() -> None:
    frame = apply_report_semantics(build_query_frame(
        {
            "report_type": "roadmap",
            "metrics": ["plan"],
            "period": {"label": "апрель"},
        },
    ))

    result = check_roadmap_compatibility(frame, "апрель")

    assert result.valid is False
    assert result.error == "metric_not_supported_for_roadmap"
    assert 'нет показателя "план"' in result.message
