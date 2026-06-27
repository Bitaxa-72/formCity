from app.pipeline.domain.common import *


class NonProjectExpensesDomainMixin:
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
