import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentsReportSource, ModelSource, NonProjectExpenseFact, PaymentCalendarFact, RoadmapStep, SalesPlanExecutionSource, SalesReportFact, SalesReportSource, StockForSaleFact, StockForSaleSource, SummarySource
from app.pipeline.query_frame import QueryFrame, QueryPeriod


MAX_AUTO_ARTICLE_MATCHES = 3
MIN_FUZZY_SCORE = 0.68
STRONG_ARTICLE_SCORE = 0.9
ARTICLE_SCORE_GAP = 0.12
MONTH_NAMES = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "мая": 5,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}
MONTH_LABELS = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}
PROJECT_LABELS = {
    "obvodny": "Обводному",
    "moskovsky": "Московскому",
    "evgenievsky": "Евгеньевскому",
    "all": "всем проектам",
}
PROJECT_LIST_LABELS = {
    "obvodny": "Обводный",
    "moskovsky": "Московский",
    "evgenievsky": "Евгеньевский",
    "all": "Все проекты",
}
MODEL_METRIC_HELP = (
    "Уточните показатель модели.\n\n"
    "Можно спросить, например:\n"
    "- выручка\n"
    "- себестоимость продаж\n"
    "- валовая прибыль\n"
    "- чистая прибыль\n"
    "- NPV\n"
    "- ROE\n"
    "- LLCR\n"
    "- общая площадь\n"
    "- количество помещений\n"
    "- ПИР\n\n"
    "Также можно запросить: краткую сводку модели, доступные показатели или доступные срезы."
)
NON_PROJECT_EXPENSES_ITEM_KIND_LABELS = {
    "lost_income": "недополученные доходы",
    "debt_receivable": "ДЗ",
    "non_project_expenses_total": "итог непроектных расходов",
    "personal": "личное",
    "admin_expenses": "АХР",
    "evgenievsky": "ЕВГ",
    "legal_entity": "юрлица",
    "fit_out": "отделочные работы",
    "commercial": "коммерческие расходы",
    "furniture": "мебелировка",
    "construction": "строительные работы",
    "developer_maintenance": "содержание застройщика",
    "object_maintenance": "содержание объекта и техзаказчик",
    "finance": "финансовые расходы",
    "pir": "ПИР",
    "other_income_expense": "прочие доходы и расходы",
    "other": "прочее",
}


@dataclass(frozen=True)
class ArticleCandidate:
    value: str
    score: float


@dataclass(frozen=True)
class DomainResolution:
    valid: bool
    frame: QueryFrame
    errors: list[str] = field(default_factory=list)
    clarification_question: str | None = None
    details: dict[str, object] = field(default_factory=dict)


def normalize_search_text(value: str) -> str:
    normalized = value.lower().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def collapse_repeated_letters(value: str) -> str:
    return re.sub(r"([a-zа-я])\1+", r"\1", value)


def article_search_variants(value: str) -> list[str]:
    normalized = normalize_search_text(value)
    collapsed = collapse_repeated_letters(normalized)
    return list(dict.fromkeys(item for item in [normalized, collapsed] if item))


def score_normalized_article(normalized_query: str, normalized_article: str) -> float:
    if not normalized_query or not normalized_article:
        return 0
    if normalized_query == normalized_article:
        return 1
    if normalized_query in normalized_article:
        return 0.92
    if normalized_query.startswith("налог") and "налог" in normalized_article:
        return 0.9
    if normalized_query.startswith("оплат") and "оплат" in normalized_article:
        return 0.9

    query_tokens = normalized_query.split()
    article_tokens = normalized_article.split()
    if query_tokens and all(token in article_tokens for token in query_tokens):
        return 0.86

    best_token_score = max(
        (SequenceMatcher(None, query_token, article_token).ratio() for query_token in query_tokens for article_token in article_tokens),
        default=0,
    )
    phrase_score = SequenceMatcher(None, normalized_query, normalized_article).ratio()
    return max(best_token_score * 0.9, phrase_score)


def score_article(query: str, article: str) -> float:
    return max(
        (
            score_normalized_article(normalized_query, normalized_article)
            for normalized_query in article_search_variants(query)
            for normalized_article in article_search_variants(article)
        ),
        default=0,
    )


def build_article_clarification(candidates: list[ArticleCandidate]) -> str:
    options = ", ".join(candidate.value for candidate in candidates[:MAX_AUTO_ARTICLE_MATCHES])
    return f"Уточните статью. Нашел несколько похожих вариантов: {options}."


def choose_article_from_candidates(candidates: list[ArticleCandidate]) -> str | None:
    if not candidates:
        return None

    exact_matches = [candidate.value for candidate in candidates if candidate.score == 1]
    if len(exact_matches) == 1:
        return exact_matches[0]

    strong_matches = [candidate for candidate in candidates if candidate.score >= STRONG_ARTICLE_SCORE]
    if len(strong_matches) == 1:
        return strong_matches[0].value

    if len(candidates) > 1 and candidates[0].score >= STRONG_ARTICLE_SCORE and candidates[0].score - candidates[1].score >= ARTICLE_SCORE_GAP:
        return candidates[0].value

    return None


def select_article_from_options(query: str, options: list[str]) -> str | None:
    candidates = sorted(
        [ArticleCandidate(value=option, score=score_article(query, option)) for option in options],
        key=lambda candidate: (-candidate.score, candidate.value),
    )
    return choose_article_from_candidates(candidates)


def format_requested_article(value: str) -> str:
    stripped = value.strip()
    return stripped[:1].upper() + stripped[1:] if stripped else value


def format_project_phrase(project: str | None) -> str:
    return PROJECT_LABELS.get(project or "all", project or "всем проектам")


def format_project_list(projects: list[str]) -> str:
    return ", ".join(PROJECT_LIST_LABELS.get(project, project) for project in projects)


def format_period_phrase(period: QueryPeriod) -> str:
    from_date = parse_iso_date(period.from_date)
    if from_date:
        return f"{MONTH_LABELS[from_date.month]} {from_date.year}"
    return period.label or "весь доступный период"


def build_missing_article_message(article: str, frame: QueryFrame) -> str:
    return (
        f"Не нашел статью \"{format_requested_article(article)}\" в платежном календаре "
        f"по {format_project_phrase(frame.project)} за {format_period_phrase(frame.period)}. "
        "Могу показать доступные статьи за этот период."
    )


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def month_end(value: date) -> date:
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def format_periods(periods: list[date]) -> str:
    return ", ".join(period.strftime("%Y-%m") for period in periods)


def is_all_period_label(label: str | None) -> bool:
    normalized = normalize_search_text(label or "")
    return normalized in {"весь период", "весь доступный период", "all", "whole period"}


def month_from_label(label: str | None) -> int | None:
    normalized = normalize_search_text(label or "")
    for marker, month in MONTH_NAMES.items():
        if marker in normalized:
            return month
    return None


def months_from_label(label: str | None) -> list[int]:
    normalized = normalize_search_text(label or "")
    months = [
        (normalized.find(marker), month)
        for marker, month in MONTH_NAMES.items()
        if marker in normalized
    ]
    ordered_months = [month for _, month in sorted(months)]
    return list(dict.fromkeys(ordered_months))


def year_from_label(label: str | None) -> int | None:
    match = re.search(r"\b(20\d{2})\b", label or "")
    return int(match.group(1)) if match else None


def period_range_from_label(label: str | None, periods: list[date]) -> tuple[date, date] | None:
    normalized = normalize_search_text(label or "")
    if not any(marker in normalized for marker in {" с ", "по", "до", "между"}):
        return None

    months = months_from_label(label)
    if len(months) < 2:
        return None

    year = year_from_label(label) or (periods[-1].year if periods else date.today().year)
    from_month = months[0]
    to_month = months[-1]
    from_year = year
    to_year = year + 1 if to_month < from_month else year
    return date(from_year, from_month, 1), month_end(date(to_year, to_month, 1))
