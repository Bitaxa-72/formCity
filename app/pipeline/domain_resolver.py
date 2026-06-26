import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelSource, NonProjectExpenseFact, PaymentCalendarFact, RoadmapStep
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


class DomainResolver:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load_payment_calendar_articles(self, frame: QueryFrame) -> list[str]:
        statement = select(PaymentCalendarFact.article).distinct()
        if frame.project and frame.project != "all":
            statement = statement.where(PaymentCalendarFact.project == frame.project)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date:
            statement = statement.where(PaymentCalendarFact.period_month >= month_start(from_date))
        if to_date:
            statement = statement.where(PaymentCalendarFact.period_month <= month_start(to_date))

        article_kind = frame.filters.get("article_kind")
        if isinstance(article_kind, str):
            statement = statement.where(PaymentCalendarFact.article_kind == article_kind)
        elif isinstance(article_kind, list):
            statement = statement.where(PaymentCalendarFact.article_kind.in_(article_kind))

        return list(self.db.execute(statement.order_by(PaymentCalendarFact.article)).scalars().all())

    def load_payment_calendar_articles_for_period(self, project: str | None, period: dict[str, str | None]) -> list[str]:
        statement = select(PaymentCalendarFact.article).distinct()
        if project and project != "all":
            statement = statement.where(PaymentCalendarFact.project == project)

        from_date = parse_iso_date(period.get("from"))
        to_date = parse_iso_date(period.get("to"))
        if from_date:
            statement = statement.where(PaymentCalendarFact.period_month >= month_start(from_date))
        if to_date:
            statement = statement.where(PaymentCalendarFact.period_month <= month_start(to_date))

        return list(self.db.execute(statement.order_by(PaymentCalendarFact.article)).scalars().all())

    def load_payment_calendar_projects(self) -> list[str]:
        statement = select(PaymentCalendarFact.project).distinct().order_by(PaymentCalendarFact.project)
        return list(self.db.execute(statement).scalars().all())

    def load_payment_calendar_periods(self, frame: QueryFrame) -> list[date]:
        statement = select(PaymentCalendarFact.period_month).distinct()
        if frame.project and frame.project != "all":
            statement = statement.where(PaymentCalendarFact.project == frame.project)
        return list(self.db.execute(statement.order_by(PaymentCalendarFact.period_month)).scalars().all())

    def resolve_payment_calendar_project(self, frame: QueryFrame) -> DomainResolution:
        if not frame.project or frame.project == "all":
            return DomainResolution(valid=True, frame=frame)

        projects = self.load_payment_calendar_projects()
        if frame.project in projects:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["project_data_not_found"],
            clarification_question=(
                f"По проекту {format_project_phrase(frame.project)} нет данных в платежном календаре. "
                f"Доступные проекты: {format_project_list(projects)}."
            ),
        )

    def normalize_payment_calendar_period(self, frame: QueryFrame) -> QueryFrame:
        periods = self.load_payment_calendar_periods(frame)
        period_range = period_range_from_label(frame.period.label, periods)
        if period_range:
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = period_range[0].isoformat()
            period_data["to"] = period_range[1].isoformat()
            return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

        month = month_from_label(frame.period.label)
        year = year_from_label(frame.period.label)
        if month and periods:
            matched_periods = [
                period
                for period in periods
                if period.month == month and (year is None or period.year == year)
            ]
            if matched_periods:
                selected_period = max(matched_periods)
                period_data = frame.period.model_dump(by_alias=True)
                period_data["from"] = selected_period.isoformat()
                period_data["to"] = month_end(selected_period).isoformat()
                return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})
            if not is_all_period_label(frame.period.label):
                period_data = frame.period.model_dump(by_alias=True)
                year_to_use = year or (periods[-1].year if periods else date.today().year)
                missing_period = date(year_to_use, month, 1)
                period_data["from"] = missing_period.isoformat()
                period_data["to"] = month_end(missing_period).isoformat()
                return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date is None and to_date is None:
            return frame

        period_data = frame.period.model_dump(by_alias=True)
        if from_date:
            period_data["from"] = month_start(from_date).isoformat()
        if to_date:
            period_data["to"] = month_end(to_date).isoformat()
        return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

    def resolve_payment_calendar_period(self, frame: QueryFrame) -> DomainResolution:
        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date is None and to_date is None:
            return DomainResolution(valid=True, frame=frame)

        from_month = month_start(from_date) if from_date else None
        to_month = month_start(to_date) if to_date else None
        periods = self.load_payment_calendar_periods(frame)
        matched_periods = [
            period
            for period in periods
            if (from_month is None or period >= from_month) and (to_month is None or period <= to_month)
        ]
        if matched_periods:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["period_data_not_found"],
            clarification_question=f"За указанный период нет данных. Доступные периоды: {format_periods(periods)}.",
        )

    def find_article_candidates(self, frame: QueryFrame, query: str) -> list[ArticleCandidate]:
        candidates = [
            ArticleCandidate(value=article, score=score_article(query, article))
            for article in self.load_payment_calendar_articles(frame)
        ]
        matched = [candidate for candidate in candidates if candidate.score >= MIN_FUZZY_SCORE]
        return sorted(matched, key=lambda candidate: (-candidate.score, candidate.value))

    def resolve_payment_calendar_article(self, frame: QueryFrame) -> DomainResolution:
        article = frame.filters.get("article")
        if not isinstance(article, str):
            return DomainResolution(valid=True, frame=frame)

        candidates = self.find_article_candidates(frame, article)
        selected_article = choose_article_from_candidates(candidates)
        if selected_article:
            filters = dict(frame.filters)
            filters["article"] = selected_article
            return DomainResolution(
                valid=True,
                frame=frame.model_copy(update={"filters": filters}),
            )

        if not candidates:
            return DomainResolution(
                valid=False,
                frame=frame,
                errors=["article_not_found"],
                clarification_question=build_missing_article_message(article, frame),
            )

        if len(candidates) > MAX_AUTO_ARTICLE_MATCHES:
            return DomainResolution(
                valid=False,
                frame=frame,
                errors=["article_ambiguous"],
                clarification_question=build_article_clarification(candidates),
                details={
                    "clarification_kind": "article",
                    "article_candidates": [candidate.value for candidate in candidates[:MAX_AUTO_ARTICLE_MATCHES]],
                },
            )

        resolved_articles = [candidate.value for candidate in candidates]
        filters = dict(frame.filters)
        filters["article"] = resolved_articles[0] if len(resolved_articles) == 1 else resolved_articles

        group_by = list(frame.group_by)
        if len(resolved_articles) > 1 and "article" not in group_by:
            group_by.append("article")

        return DomainResolution(
            valid=True,
            frame=frame.model_copy(update={"filters": filters, "group_by": group_by}),
        )

    def load_roadmap_periods(self) -> list[date]:
        statement = select(RoadmapStep.period_month).distinct().order_by(RoadmapStep.period_month)
        return list(self.db.execute(statement).scalars().all())

    def normalize_roadmap_period(self, frame: QueryFrame) -> QueryFrame:
        periods = self.load_roadmap_periods()
        if not periods:
            return frame.model_copy(update={"project": "all"})

        period_range = period_range_from_label(frame.period.label, periods)
        if period_range:
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = period_range[0].isoformat()
            period_data["to"] = period_range[1].isoformat()
            return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

        month = month_from_label(frame.period.label)
        year = year_from_label(frame.period.label)
        if month:
            matched_periods = [
                period
                for period in periods
                if period.month == month and (year is None or period.year == year)
            ]
            if matched_periods:
                selected_period = max(matched_periods)
                period_data = frame.period.model_dump(by_alias=True)
                period_data["from"] = selected_period.isoformat()
                period_data["to"] = month_end(selected_period).isoformat()
                period_data["label"] = f"{MONTH_LABELS[selected_period.month]} {selected_period.year}"
                return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

            period_data = frame.period.model_dump(by_alias=True)
            year_to_use = year or periods[-1].year
            missing_period = date(year_to_use, month, 1)
            period_data["from"] = missing_period.isoformat()
            period_data["to"] = month_end(missing_period).isoformat()
            period_data["label"] = f"{MONTH_LABELS[missing_period.month]} {missing_period.year}"
            return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date or to_date:
            period_data = frame.period.model_dump(by_alias=True)
            if from_date:
                period_data["from"] = month_start(from_date).isoformat()
            if to_date:
                period_data["to"] = month_end(to_date).isoformat()
            return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

        if frame.intent == "dimension_query" and frame.dimension == "period_month":
            return frame.model_copy(update={"project": "all"})

        selected_period = periods[-1]
        period_data = frame.period.model_dump(by_alias=True)
        period_data["from"] = selected_period.isoformat()
        period_data["to"] = month_end(selected_period).isoformat()
        period_data["label"] = f"последний актуальный месяц, {MONTH_LABELS[selected_period.month]} {selected_period.year}"
        return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

    def resolve_roadmap_period(self, frame: QueryFrame) -> DomainResolution:
        if frame.intent == "dimension_query" and frame.dimension == "period_month":
            return DomainResolution(valid=True, frame=frame)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date is None and to_date is None:
            return DomainResolution(valid=True, frame=frame)

        from_month = month_start(from_date) if from_date else None
        to_month = month_start(to_date) if to_date else None
        periods = self.load_roadmap_periods()
        matched_periods = [
            period
            for period in periods
            if (from_month is None or period >= from_month) and (to_month is None or period <= to_month)
        ]
        if matched_periods:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["period_data_not_found"],
            clarification_question=f"За указанный период нет данных по дорожной карте. Доступные периоды: {format_periods(periods)}.",
        )

    def resolve_roadmap(self, frame: QueryFrame) -> DomainResolution:
        normalized_frame = self.normalize_roadmap_period(frame)
        return self.resolve_roadmap_period(normalized_frame)

    def load_non_project_expenses_periods(self) -> list[date]:
        statement = select(NonProjectExpenseFact.period_month).distinct().order_by(NonProjectExpenseFact.period_month)
        return list(self.db.execute(statement).scalars().all())

    def load_non_project_expenses_values(self, frame: QueryFrame, column: str) -> list[str]:
        model_column = getattr(NonProjectExpenseFact, column)
        statement = select(model_column).distinct().where(model_column.is_not(None))

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date:
            statement = statement.where(NonProjectExpenseFact.period_month >= month_start(from_date))
        if to_date:
            statement = statement.where(NonProjectExpenseFact.period_month <= month_start(to_date))

        item_kind = frame.filters.get("item_kind")
        if column != "item_kind":
            if isinstance(item_kind, str):
                statement = statement.where(NonProjectExpenseFact.item_kind == item_kind)
            elif isinstance(item_kind, list):
                statement = statement.where(NonProjectExpenseFact.item_kind.in_(item_kind))

        row_type = frame.filters.get("row_type")
        if column != "row_type":
            if isinstance(row_type, str):
                statement = statement.where(NonProjectExpenseFact.row_type == row_type)
            elif isinstance(row_type, list):
                statement = statement.where(NonProjectExpenseFact.row_type.in_(row_type))

        return list(self.db.execute(statement.order_by(model_column)).scalars().all())

    def normalize_non_project_expenses_period(self, frame: QueryFrame) -> QueryFrame:
        periods = self.load_non_project_expenses_periods()
        if not periods:
            return frame.model_copy(update={"project": "all"})

        if frame.intent == "dimension_query" and frame.dimension == "period_month":
            return frame.model_copy(update={"project": "all"})

        period_range = period_range_from_label(frame.period.label, periods)
        if period_range:
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = period_range[0].isoformat()
            period_data["to"] = period_range[1].isoformat()
            return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

        month = month_from_label(frame.period.label)
        year = year_from_label(frame.period.label)
        if month:
            matched = [
                period
                for period in periods
                if period.month == month and (year is None or period.year == year)
            ]
            if matched:
                selected = max(matched)
                period_data = frame.period.model_dump(by_alias=True)
                period_data["from"] = selected.isoformat()
                period_data["to"] = month_end(selected).isoformat()
                period_data["label"] = f"{MONTH_LABELS[selected.month]} {selected.year}"
                return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

            missing = date(year or periods[-1].year, month, 1)
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = missing.isoformat()
            period_data["to"] = month_end(missing).isoformat()
            period_data["label"] = f"{MONTH_LABELS[missing.month]} {missing.year}"
            return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date or to_date:
            period_data = frame.period.model_dump(by_alias=True)
            if from_date:
                period_data["from"] = month_start(from_date).isoformat()
            if to_date:
                period_data["to"] = month_end(to_date).isoformat()
            return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

        selected = periods[-1]
        period_data = frame.period.model_dump(by_alias=True)
        period_data["from"] = selected.isoformat()
        period_data["to"] = month_end(selected).isoformat()
        period_data["label"] = f"последний актуальный месяц, {MONTH_LABELS[selected.month]} {selected.year}"
        return frame.model_copy(update={"project": "all", "period": QueryPeriod.model_validate(period_data)})

    def resolve_non_project_expenses_period(self, frame: QueryFrame) -> DomainResolution:
        if frame.intent == "dimension_query" and frame.dimension == "period_month":
            return DomainResolution(valid=True, frame=frame)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date is None and to_date is None:
            return DomainResolution(valid=True, frame=frame)

        from_month = month_start(from_date) if from_date else None
        to_month = month_start(to_date) if to_date else None
        periods = self.load_non_project_expenses_periods()
        matched = [
            period
            for period in periods
            if (from_month is None or period >= from_month) and (to_month is None or period <= to_month)
        ]
        if matched:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["period_data_not_found"],
            clarification_question=f"За указанный период нет данных по непроектным расходам. Доступные периоды: {format_periods(periods)}.",
        )

    def find_non_project_expenses_candidates(self, frame: QueryFrame, column: str, query: str) -> list[ArticleCandidate]:
        candidates = [
            ArticleCandidate(value=value, score=score_article(query, value))
            for value in self.load_non_project_expenses_values(frame, column)
        ]
        matched = [candidate for candidate in candidates if candidate.score >= MIN_FUZZY_SCORE]
        return sorted(matched, key=lambda candidate: (-candidate.score, candidate.value))

    def resolve_non_project_expenses_text_filter(self, frame: QueryFrame, filter_name: str, column: str, label: str) -> DomainResolution:
        value = frame.filters.get(filter_name)
        if not isinstance(value, str):
            return DomainResolution(valid=True, frame=frame)

        candidates = self.find_non_project_expenses_candidates(frame, column, value)
        selected = choose_article_from_candidates(candidates)
        if selected:
            filters = dict(frame.filters)
            filters[filter_name] = selected
            return DomainResolution(valid=True, frame=frame.model_copy(update={"filters": filters}))

        if not candidates:
            return DomainResolution(
                valid=False,
                frame=frame,
                errors=[f"{filter_name}_not_found"],
                clarification_question=(
                    f"Не нашел {label} \"{format_requested_article(value)}\" в непроектных расходах за {format_period_phrase(frame.period)}. "
                    "Могу показать доступные строки и категории за этот период."
                ),
            )

        if len(candidates) > MAX_AUTO_ARTICLE_MATCHES:
            options = ", ".join(candidate.value for candidate in candidates[:MAX_AUTO_ARTICLE_MATCHES])
            return DomainResolution(
                valid=False,
                frame=frame,
                errors=[f"{filter_name}_ambiguous"],
                clarification_question=f"Уточните {label}. Нашел несколько похожих вариантов: {options}.",
            )

        resolved = [candidate.value for candidate in candidates]
        filters = dict(frame.filters)
        filters[filter_name] = resolved[0] if len(resolved) == 1 else resolved
        group_by = list(frame.group_by)
        if len(resolved) > 1 and column not in group_by:
            group_by.append(column)
        return DomainResolution(valid=True, frame=frame.model_copy(update={"filters": filters, "group_by": group_by}))

    def resolve_non_project_expenses_item_kind(self, frame: QueryFrame) -> DomainResolution:
        value = frame.filters.get("item_kind")
        if not isinstance(value, str):
            return DomainResolution(valid=True, frame=frame)

        available = set(self.load_non_project_expenses_values(frame, "item_kind"))
        if value in available:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["item_kind_not_found"],
            clarification_question=(
                f"Не нашел тип \"{NON_PROJECT_EXPENSES_ITEM_KIND_LABELS.get(value, value)}\" в непроектных расходах за {format_period_phrase(frame.period)}. "
                "Могу показать доступные типы строк за этот период."
            ),
        )

    def resolve_non_project_expenses(self, frame: QueryFrame) -> DomainResolution:
        frame = self.normalize_non_project_expenses_period(frame)
        period_resolution = self.resolve_non_project_expenses_period(frame)
        if not period_resolution.valid:
            return period_resolution

        item_kind_resolution = self.resolve_non_project_expenses_item_kind(period_resolution.frame)
        if not item_kind_resolution.valid:
            return item_kind_resolution

        category_resolution = self.resolve_non_project_expenses_text_filter(
            item_kind_resolution.frame,
            "fm_category",
            "fm_category",
            "категорию",
        )
        if not category_resolution.valid:
            return category_resolution

        return self.resolve_non_project_expenses_text_filter(
            category_resolution.frame,
            "item_name",
            "item_name",
            "строку",
        )

    def load_model_projects(self) -> list[str]:
        statement = select(ModelSource.project).distinct().order_by(ModelSource.project)
        return list(self.db.execute(statement).scalars().all())

    def load_model_snapshots(self, frame: QueryFrame) -> list[date]:
        statement = select(ModelSource.snapshot_month).distinct()
        if frame.project and frame.project != "all":
            statement = statement.where(ModelSource.project == frame.project)
        return list(self.db.execute(statement.order_by(ModelSource.snapshot_month)).scalars().all())

    def resolve_model_project(self, frame: QueryFrame) -> DomainResolution:
        project = frame.project or "obvodny"
        projects = self.load_model_projects()
        if project == "all":
            project = "obvodny"
        if project in projects:
            return DomainResolution(valid=True, frame=frame.model_copy(update={"project": project}))
        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["project_data_not_found"],
            clarification_question=f"По проекту {PROJECT_LIST_LABELS.get(project, project)} модель пока не загружена. Доступные проекты: {format_project_list(projects)}.",
        )

    def normalize_model_snapshot(self, frame: QueryFrame) -> QueryFrame:
        snapshots = self.load_model_snapshots(frame)
        if not snapshots:
            return frame

        if frame.intent == "dimension_query" and frame.dimension in {"snapshot_month", "metric"}:
            return frame

        month = month_from_label(frame.period.label)
        year = year_from_label(frame.period.label)
        if month:
            matched = [
                snapshot
                for snapshot in snapshots
                if snapshot.month == month and (year is None or snapshot.year == year)
            ]
            if matched:
                selected = max(matched)
                period_data = frame.period.model_dump(by_alias=True)
                period_data["from"] = selected.isoformat()
                period_data["to"] = month_end(selected).isoformat()
                period_data["label"] = f"срез модели: {MONTH_LABELS[selected.month]} {selected.year}"
                return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

            missing = date(year or snapshots[-1].year, month, 1)
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = missing.isoformat()
            period_data["to"] = month_end(missing).isoformat()
            period_data["label"] = f"срез модели: {MONTH_LABELS[missing.month]} {missing.year}"
            return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date or to_date:
            period_data = frame.period.model_dump(by_alias=True)
            if from_date:
                period_data["from"] = month_start(from_date).isoformat()
            if to_date:
                period_data["to"] = month_end(to_date).isoformat()
            return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

        selected = snapshots[-1]
        period_data = frame.period.model_dump(by_alias=True)
        period_data["from"] = selected.isoformat()
        period_data["to"] = month_end(selected).isoformat()
        period_data["label"] = f"последний доступный срез модели: {MONTH_LABELS[selected.month]} {selected.year}"
        return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

    def resolve_model_snapshot(self, frame: QueryFrame) -> DomainResolution:
        if frame.intent == "dimension_query" and frame.dimension in {"snapshot_month", "metric"}:
            return DomainResolution(valid=True, frame=frame)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        snapshots = self.load_model_snapshots(frame)
        if from_date is None and to_date is None:
            return DomainResolution(valid=True, frame=frame)

        from_month = month_start(from_date) if from_date else None
        to_month = month_start(to_date) if to_date else None
        matched = [
            snapshot
            for snapshot in snapshots
            if (from_month is None or snapshot >= from_month) and (to_month is None or snapshot <= to_month)
        ]
        if matched:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["model_snapshot_not_found"],
            clarification_question=f"За указанный срез модели нет данных. Доступные срезы: {format_periods(snapshots)}.",
        )

    def resolve_model(self, frame: QueryFrame) -> DomainResolution:
        project_resolution = self.resolve_model_project(frame)
        if not project_resolution.valid:
            return project_resolution
        normalized_frame = self.normalize_model_snapshot(project_resolution.frame)
        return self.resolve_model_snapshot(normalized_frame)

    def resolve(self, frame: QueryFrame) -> DomainResolution:
        if not frame.ready:
            return DomainResolution(valid=True, frame=frame)
        if frame.report_type == "model":
            return self.resolve_model(frame)
        if frame.report_type == "non_project_expenses":
            return self.resolve_non_project_expenses(frame)
        if frame.report_type == "roadmap":
            return self.resolve_roadmap(frame)
        if frame.report_type != "payment_calendar":
            return DomainResolution(valid=True, frame=frame)

        project_resolution = self.resolve_payment_calendar_project(frame)
        if not project_resolution.valid:
            return project_resolution

        frame = self.normalize_payment_calendar_period(project_resolution.frame)
        period_resolution = self.resolve_payment_calendar_period(frame)
        if not period_resolution.valid:
            return period_resolution

        return self.resolve_payment_calendar_article(period_resolution.frame)
