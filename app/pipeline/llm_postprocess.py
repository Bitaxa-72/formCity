from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta
from app.pipeline.dimension_clarification import resolve_dimension_clarification
from app.pipeline.domain_resolver import select_article_from_options, normalize_search_text


def apply_article_clarification_selection(
    state: dict[str, object] | None,
    parsed_response: LLMParsedResponse,
    user_text: str | None,
) -> LLMParsedResponse:
    if not state or state.get("awaiting_clarification") is not True or state.get("clarification_kind") != "article":
        return parsed_response

    options = state.get("clarification_options")
    if not isinstance(options, list) or not all(isinstance(option, str) for option in options):
        return parsed_response

    selected_article = select_article_from_options(user_text or "", options)
    if not selected_article:
        return parsed_response

    delta_data = parsed_response.state_delta.model_dump(mode="json", by_alias=True, exclude_none=True)
    filters = dict(delta_data.get("filters") or {})
    filters["article"] = selected_article
    delta_data["filters"] = filters
    return parsed_response.model_copy(
        update={
            "state_delta": StateDelta.model_validate(delta_data),
            "needs_clarification": False,
            "clarification_question": None,
        },
    )


def apply_dimension_clarification_selection(
    state: dict[str, object] | None,
    parsed_response: LLMParsedResponse,
    user_text: str | None,
) -> LLMParsedResponse:
    if not state or state.get("awaiting_clarification") is not True or state.get("clarification_kind") != "dimension":
        return parsed_response

    resolution = resolve_dimension_clarification(user_text)
    if not resolution.matched or not resolution.dimension:
        return parsed_response

    delta_data = parsed_response.state_delta.model_dump(mode="json", by_alias=True, exclude_none=True)
    delta_data["dimension"] = resolution.dimension
    delta_data.pop("metrics", None)
    if resolution.filters:
        filters = dict(delta_data.get("filters") or {})
        filters.update(resolution.filters)
        delta_data["filters"] = filters
    else:
        delta_data.pop("filters", None)

    return parsed_response.model_copy(
        update={
            "intent": Intent.DIMENSION_QUERY,
            "state_delta": StateDelta.model_validate(delta_data),
            "needs_clarification": False,
            "clarification_question": None,
        },
    )


def apply_dimension_query_fallback(parsed_response: LLMParsedResponse, user_text: str | None) -> LLMParsedResponse:
    normalized = normalize_search_text(user_text or "")
    if "платежн" not in normalized and "календар" not in normalized:
        return parsed_response
    if not any(marker in normalized for marker in {"какие", "какой", "список", "перечень"}):
        return parsed_response

    resolution = resolve_dimension_clarification(user_text)
    if not resolution.matched or not resolution.dimension:
        return parsed_response

    delta_data = parsed_response.state_delta.model_dump(mode="json", by_alias=True, exclude_none=True)
    delta_data["report_type"] = "payment_calendar"
    delta_data["dimension"] = resolution.dimension
    delta_data.pop("metrics", None)
    if resolution.filters:
        existing_filters = dict(delta_data.get("filters") or {})
        existing_filters.update(resolution.filters)
        delta_data["filters"] = existing_filters
    else:
        delta_data.pop("filters", None)

    return parsed_response.model_copy(
        update={
            "intent": Intent.DIMENSION_QUERY,
            "state_delta": StateDelta.model_validate(delta_data),
            "needs_clarification": False,
            "clarification_question": None,
        },
    )
