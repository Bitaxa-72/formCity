from app.pipeline.domain.common import *


class PaymentCalendarDomainMixin:
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
