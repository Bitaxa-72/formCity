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
        "что ты умеешь делать",
        "как пользоваться",
        "как пользоваться ботом",
        "как с тобой работать",
        "какие возможности",
        "какие отчеты доступны",
        "какие отчеты есть",
        "какие типы отчетов доступны",
        "какие типы отчетов есть",
        "список отчетов",
        "доступные отчеты",
        "какие данные есть",
        "какие данные доступны",
        "что доступно",
        "что можно спросить",
        "помощь",
        "помоги",
        "подскажи что можно спросить",
        "help",
    }
    if normalized in direct_phrases:
        return True

    has_capability_word = any(marker in normalized for marker in {"умееш", "можеш", "возможност"})
    has_question_word = any(marker in normalized for marker in {"что", "чем", "как", "какие"})
    has_report_list_word = "отчет" in normalized and any(marker in normalized for marker in {"какие", "список", "доступн", "есть"})
    has_data_list_word = "данн" in normalized and any(marker in normalized for marker in {"какие", "что", "доступн", "есть"})
    has_usage_word = "пользоваться" in normalized and "бот" in normalized
    return (has_capability_word and has_question_word) or has_report_list_word or has_data_list_word or has_usage_word


def should_skip_pdf_report(response_data: object) -> bool:
    source = getattr(response_data, "source", None)
    return (
        isinstance(source, dict)
        and source.get("report_type") == "model"
        and source.get("view") in {"model_available_metrics", "model_raw_rows", "model_raw_search"}
    )


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
