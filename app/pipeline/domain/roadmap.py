from app.pipeline.domain.common import *


class RoadmapDomainMixin:
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
