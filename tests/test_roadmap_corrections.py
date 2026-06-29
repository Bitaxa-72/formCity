from app.pipeline.failed_query import CONTEXT_BLOCKED_AFTER_ERROR, FAILED_QUERY_ERROR, FAILED_QUERY_STATE
from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_semantics import apply_report_semantics
from app.reports.roadmap.compatibility import check_roadmap_compatibility
from app.reports.roadmap.corrections import (
    ROADMAP_ACTION_CLARIFICATION,
    build_explicit_roadmap_unsupported_metric_correction,
    build_failed_roadmap_correction,
    build_roadmap_context_correction,
    resolve_roadmap_recovery,
)


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
    assert parsed.state_delta.metrics == []
    assert parsed.needs_clarification is True
    assert parsed.clarification_question == ROADMAP_ACTION_CLARIFICATION


def test_explicit_roadmap_unsupported_metric_reaches_roadmap_compatibility() -> None:
    parsed = build_explicit_roadmap_unsupported_metric_correction("дорожная карта план по рекламе")

    assert parsed is not None
    assert parsed.state_delta.report_type == "roadmap"
    assert parsed.state_delta.project == "all"
    assert parsed.state_delta.metrics == ["duration_min"]


def test_failed_roadmap_periods_followup_clears_failed_period() -> None:
    state, parsed = build_failed_roadmap_correction(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "metric_not_supported_for_roadmap",
            FAILED_QUERY_STATE: {
                "report_type": "roadmap",
                "project": "all",
                "period": {"label": "апрель"},
                "metrics": ["plan"],
                "view": None,
                "filters": {},
                "group_by": [],
            },
        },
        "периоды",
    )

    assert parsed is not None
    assert state["period"] == {"from": None, "to": None, "label": None}
    assert parsed.intent == "dimension_query"
    assert parsed.state_delta.dimension == "period_month"


def test_roadmap_context_steps_followup_switches_from_duration_to_steps() -> None:
    parsed = build_roadmap_context_correction(
        {
            "report_type": "roadmap",
            "period": {"label": "апрель"},
            "view": "total_duration",
            "metrics": ["duration_min", "duration_max"],
        },
        "этапы",
    )

    assert parsed is not None
    assert parsed.state_delta.view == "roadmap_steps"
    assert parsed.state_delta.metrics == ["duration_min", "duration_max"]
    assert parsed.state_delta.filters == {}
    assert parsed.state_delta.group_by == []


def test_roadmap_semantics_keeps_clarification_not_ready() -> None:
    frame = apply_report_semantics(build_query_frame(
        {
            "report_type": "roadmap",
            "project": "all",
            "period": {"label": "апрель"},
            "metrics": [],
            "awaiting_clarification": True,
            "clarification_target": ROADMAP_ACTION_CLARIFICATION,
        },
    ))

    assert frame.ready is False
    assert frame.clarification_question == ROADMAP_ACTION_CLARIFICATION


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


def test_roadmap_compatibility_rejects_sensitive_request() -> None:
    frame = apply_report_semantics(build_query_frame(
        {
            "report_type": "roadmap",
            "metrics": ["duration_min"],
            "period": {"label": "апрель"},
        },
    ))

    result = check_roadmap_compatibility(frame, "дорожная карта телефоны участников")

    assert result.valid is False
    assert result.error == "sensitive_field_not_supported_for_roadmap"
    assert 'не вывожу "телефоны"' in result.message


def test_roadmap_compatibility_uses_current_unsupported_metric_text() -> None:
    frame = apply_report_semantics(build_query_frame(
        {
            "report_type": "roadmap",
            "metrics": ["duration_min"],
            "period": {"label": "апрель"},
        },
    ))

    result = check_roadmap_compatibility(frame, "дорожная карта сделки")

    assert result.valid is False
    assert result.error == "metric_not_supported_for_roadmap"
    assert 'нет показателя "количество сделок"' in result.message
