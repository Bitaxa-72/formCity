from copy import deepcopy
from typing import Any

from app.llm_dictionary import Intent
from app.llm_parser import LLMParsedResponse, StateDelta


DEFAULT_DIALOG_STATE: dict[str, Any] = {
    "report_type": None,
    "project": None,
    "period": {
        "from": None,
        "to": None,
        "label": None,
    },
    "metrics": [],
    "filters": {},
    "group_by": [],
    "sort": None,
    "limit": None,
    "last_intent": None,
    "awaiting_clarification": False,
    "clarification_target": None,
}


def empty_dialog_state() -> dict[str, Any]:
    return deepcopy(DEFAULT_DIALOG_STATE)


def normalize_state(state: dict[str, Any] | None) -> dict[str, Any]:
    normalized = empty_dialog_state()
    for key, value in (state or {}).items():
        if key == "period" and isinstance(value, dict):
            normalized["period"].update(value)
        elif key == "filters" and isinstance(value, dict):
            normalized["filters"].update(value)
        elif key in normalized:
            normalized[key] = value
    return normalized


def apply_state_delta(state: dict[str, Any], delta: StateDelta) -> dict[str, Any]:
    updated = deepcopy(state)
    delta_data = delta.model_dump(mode="json", by_alias=True, exclude_none=True)

    for key, value in delta_data.items():
        if key == "period":
            updated["period"].update(value)
        elif key == "filters":
            updated["filters"].update(value)
        else:
            updated[key] = value

    return updated


def resolve_context(
    current_state: dict[str, Any] | None,
    parsed_response: LLMParsedResponse,
) -> dict[str, Any]:
    if parsed_response.intent == Intent.DATA_QUERY:
        resolved = empty_dialog_state()
    else:
        resolved = normalize_state(current_state)

    resolved = apply_state_delta(resolved, parsed_response.state_delta)
    resolved["last_intent"] = parsed_response.intent.value
    resolved["awaiting_clarification"] = parsed_response.needs_clarification
    resolved["clarification_target"] = parsed_response.clarification_question if parsed_response.needs_clarification else None

    if parsed_response.intent == Intent.MATH_ON_LAST_RESULT and parsed_response.operation:
        resolved["pending_operation"] = parsed_response.operation.model_dump(mode="json")
    else:
        resolved.pop("pending_operation", None)

    return resolved
