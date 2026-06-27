from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.metric_catalog import METRIC_CATALOG


def is_capabilities_question(text: str | None) -> bool:
    normalized = normalize_search_text(text or "")
    if not normalized:
        return False

    direct_phrases = {
        "что ты умеешь",
        "что умеешь",
        "что можешь",
        "что ты можешь",
        "как пользоваться",
        "как с тобой работать",
        "какие возможности",
        "что доступно",
        "что можно спросить",
        "помощь",
        "help",
    }
    if normalized in direct_phrases:
        return True

    has_capability_word = any(marker in normalized for marker in {"умееш", "можеш", "возможност"})
    has_question_word = any(marker in normalized for marker in {"что", "чем", "как", "какие"})
    return has_capability_word and has_question_word


def should_skip_pdf_report(response_data: object) -> bool:
    source = getattr(response_data, "source", None)
    return isinstance(source, dict) and source.get("report_type") == "model" and source.get("view") == "model_available_metrics"


def is_vague_followup_question(text: str | None) -> bool:
    normalized = normalize_search_text(text or "")
    return normalized in {
        "а что там",
        "что там",
        "покажи это",
        "покажи",
        "ну и",
        "и что",
        "что дальше",
        "что по этому",
        "что по нему",
    }


def is_unclear_roadmap_question(text: str | None) -> bool:
    normalized = normalize_search_text(text or "")
    return "дорожная карта" in normalized


def is_report_type_not_connected(report_type: str | None) -> bool:
    return bool(report_type and report_type in METRIC_CATALOG and not METRIC_CATALOG[report_type])
