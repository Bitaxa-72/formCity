from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta
from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    clear_failed_query_markers,
)


def has_roadmap_step_word(normalized_text: str) -> bool:
    words = normalized_text.split()
    return any(word.startswith("этап") or word.startswith("шаг") for word in words)


def resolve_roadmap_recovery(text: str | None) -> tuple[str, dict[str, object]] | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None

    if any(marker in normalized_text for marker in ("период", "месяц", "доступн")):
        return "dimension_query", {"dimension": "period_month", "metrics": [], "view": None, "filters": {}, "group_by": []}

    if any(marker in normalized_text for marker in ("срок", "дней", "занима", "итог")):
        return "data_query", {
            "metrics": ["duration_min", "duration_max"],
            "view": "total_duration",
            "filters": {},
            "group_by": [],
        }

    if "росреестр" in normalized_text:
        return "data_query", {
            "metrics": ["duration_min", "duration_max"],
            "view": "external_steps",
            "filters": {"action_text_contains": "РОСРЕЕСТР"},
            "group_by": [],
        }

    if "банк" in normalized_text:
        return "data_query", {
            "metrics": ["duration_min", "duration_max"],
            "view": "external_steps",
            "filters": {"action_text_contains": "БАНК"},
            "group_by": [],
        }

    if any(marker in normalized_text for marker in ("внешн", "завис")):
        return "data_query", {
            "metrics": ["duration_min", "duration_max"],
            "view": "external_steps",
            "filters": {},
            "group_by": [],
        }

    if has_roadmap_step_word(normalized_text):
        return "data_query", {
            "metrics": ["duration_min", "duration_max"],
            "view": "roadmap_steps",
            "filters": {},
            "group_by": [],
        }

    return None


def build_failed_roadmap_correction(
    state: dict[str, object] | None,
    text: str | None,
) -> tuple[dict[str, object], LLMParsedResponse] | None:
    if not state or state.get(CONTEXT_BLOCKED_AFTER_ERROR) is not True:
        return None
    if state.get(FAILED_QUERY_ERROR) != "metric_not_supported_for_roadmap":
        return None

    failed_state = state.get(FAILED_QUERY_STATE)
    if not isinstance(failed_state, dict):
        return None
    if failed_state.get("report_type") != "roadmap":
        return None

    recovery = resolve_roadmap_recovery(text)
    if recovery is None:
        return None

    intent, delta_data = recovery
    corrected_state = dict(failed_state)
    corrected_state.update(delta_data)
    corrected_state["report_type"] = "roadmap"
    corrected_state["project"] = "all"
    corrected_state["awaiting_clarification"] = False
    corrected_state["clarification_target"] = None
    corrected_state["clarification_base_state"] = None
    corrected_state["clarification_kind"] = None
    corrected_state["clarification_options"] = []
    corrected_state = clear_failed_query_markers(corrected_state)

    parsed_response = LLMParsedResponse(
        intent=Intent.DIMENSION_QUERY if intent == "dimension_query" else Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(delta_data),
        confidence=1,
    )
    return corrected_state, parsed_response
