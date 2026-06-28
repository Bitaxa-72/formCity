from dataclasses import dataclass

from app.llm.report_rules import REPORT_TYPE_ALIASES
from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


AVAILABLE_REPORTS_MESSAGE = (
    "Если нужен другой отчет, сформулируйте новый запрос полностью.\n\n"
    "Доступные отчеты:\n"
    "- платежный календарь\n"
    "- дорожная карта\n"
    "- модель\n"
    "- непроектные расходы\n"
    "- остатки в продаже\n"
    "- отчет о продажах\n"
    "- исполнение плана продаж\n"
    "- отчет по агентам\n"
    "- ДЗ и брони\n"
    "- сводный отчет"
)
REPORT_LABELS = {
    "summary": "сводном отчете",
    "model": "модели",
    "payment_calendar": "платежном календаре",
    "roadmap": "дорожной карте",
    "sales_report": "отчете о продажах",
    "sales_plan_execution": "исполнении плана продаж",
    "agents_report": "отчете по агентам",
    "stock_for_sale": "остатках в продаже",
    "debt_and_bookings": "ДЗ и бронях",
    "non_project_expenses": "непроектных расходах",
}


@dataclass(frozen=True)
class SemanticTerm:
    label: str
    aliases: tuple[str, ...]
    report_types: frozenset[str]


SEMANTIC_TERMS = (
    SemanticTerm(
        "NPV",
        ("npv",),
        frozenset({"model"}),
    ),
    SemanticTerm(
        "ROE",
        ("roe",),
        frozenset({"model"}),
    ),
    SemanticTerm(
        "LLCR",
        ("llcr",),
        frozenset({"model"}),
    ),
    SemanticTerm(
        "выручка",
        ("выручк",),
        frozenset({"model", "sales_report", "sales_plan_execution", "summary"}),
    ),
    SemanticTerm(
        "количество сделок",
        ("сделк", "количество сделок"),
        frozenset({"sales_report", "sales_plan_execution", "agents_report", "summary"}),
    ),
    SemanticTerm(
        "цена метра",
        ("цена метра", "цена м2", "цена за м2", "цена квадратного метра", "стоимость метра"),
        frozenset({"stock_for_sale", "sales_report", "sales_plan_execution", "summary"}),
    ),
    SemanticTerm(
        "квадратные метры",
        ("квадратные метры", "метры", "м2", "площадь"),
        frozenset({"model", "stock_for_sale", "sales_report", "sales_plan_execution", "agents_report", "summary"}),
    ),
    SemanticTerm(
        "этажи",
        ("этаж", "этажи", "этажам"),
        frozenset({"stock_for_sale", "summary"}),
    ),
    SemanticTerm(
        "типы помещений",
        ("типы помещений", "типам помещений", "сегменты"),
        frozenset({"stock_for_sale", "sales_report", "sales_plan_execution", "summary"}),
    ),
    SemanticTerm(
        "ФОТ",
        ("фот", "зарплат", "оплата труда"),
        frozenset({"payment_calendar", "non_project_expenses", "summary"}),
    ),
    SemanticTerm(
        "реклама",
        ("реклам", "маркетинг"),
        frozenset({"payment_calendar", "non_project_expenses", "summary"}),
    ),
)


def text_mentions_report_type(report_type: str | None, text: str | None) -> bool:
    if not report_type:
        return False
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return False
    for alias in REPORT_TYPE_ALIASES.get(report_type, []):
        normalized_alias = normalize_search_text(alias)
        if normalized_alias and normalized_alias in normalized_text:
            return True
    return False


def find_semantic_term(text: str | None) -> SemanticTerm | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None
    for term in SEMANTIC_TERMS:
        for alias in term.aliases:
            if normalize_search_text(alias) in normalized_text:
                return term
    return None


def build_semantic_mismatch_message(report_type: str, term: SemanticTerm) -> str:
    report_label = REPORT_LABELS.get(report_type, "выбранном отчете")
    return f'В {report_label} нет показателя или разреза "{term.label}".\n\n{AVAILABLE_REPORTS_MESSAGE}'


def check_semantic_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    if frame.report_type == "payment_calendar":
        return CompatibilityCheck(valid=True)
    if not text_mentions_report_type(frame.report_type, user_text):
        return CompatibilityCheck(valid=True)

    term = find_semantic_term(user_text)
    if term is None or frame.report_type in term.report_types:
        return CompatibilityCheck(valid=True)

    return CompatibilityCheck(
        valid=False,
        error="semantic_term_not_supported_for_report",
        message=build_semantic_mismatch_message(frame.report_type, term),
    )
