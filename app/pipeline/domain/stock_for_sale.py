from app.pipeline.domain.common import *


class StockForSaleDomainMixin:
    def load_stock_for_sale_projects(self) -> list[str]:
        statement = select(StockForSaleSource.project).distinct().order_by(StockForSaleSource.project)
        return list(self.db.execute(statement).scalars().all())

    def load_stock_for_sale_periods(self, frame: QueryFrame) -> list[date]:
        statement = select(StockForSaleSource.snapshot_month).distinct()
        if frame.project and frame.project != "all":
            statement = statement.where(StockForSaleSource.project == frame.project)
        return list(self.db.execute(statement.order_by(StockForSaleSource.snapshot_month)).scalars().all())

    def load_stock_for_sale_values(self, frame: QueryFrame, column: str) -> list[object]:
        model_column = getattr(StockForSaleFact, column)
        statement = select(model_column).distinct().where(model_column.is_not(None))

        if frame.project and frame.project != "all":
            statement = statement.where(StockForSaleFact.project == frame.project)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date:
            statement = statement.where(StockForSaleFact.snapshot_month >= month_start(from_date))
        if to_date:
            statement = statement.where(StockForSaleFact.snapshot_month <= month_start(to_date))

        row_type = frame.filters.get("row_type")
        if column != "row_type":
            if isinstance(row_type, str):
                statement = statement.where(StockForSaleFact.row_type == row_type)
            elif isinstance(row_type, list):
                statement = statement.where(StockForSaleFact.row_type.in_(row_type))

        property_type = frame.filters.get("property_type")
        if column != "property_type":
            if isinstance(property_type, str):
                statement = statement.where(StockForSaleFact.property_type == property_type)
            elif isinstance(property_type, list):
                statement = statement.where(StockForSaleFact.property_type.in_(property_type))

        return list(self.db.execute(statement.order_by(model_column)).scalars().all())

    def resolve_stock_for_sale_project(self, frame: QueryFrame) -> DomainResolution:
        project = frame.project or "obvodny"
        projects = self.load_stock_for_sale_projects()
        if project == "all":
            project = "obvodny"
        if project in projects:
            return DomainResolution(valid=True, frame=frame.model_copy(update={"project": project}))
        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["project_data_not_found"],
            clarification_question=f"По проекту {PROJECT_LIST_LABELS.get(project, project)} остатки в продаже пока не загружены. Доступные проекты: {format_project_list(projects)}.",
        )

    def normalize_stock_for_sale_period(self, frame: QueryFrame) -> QueryFrame:
        periods = self.load_stock_for_sale_periods(frame)
        if not periods:
            return frame

        if frame.intent == "dimension_query" and frame.dimension in {"snapshot_month", "period_month"}:
            return frame

        period_range = period_range_from_label(frame.period.label, periods)
        if period_range:
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = period_range[0].isoformat()
            period_data["to"] = period_range[1].isoformat()
            return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

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
                period_data["label"] = f"срез остатков: {MONTH_LABELS[selected.month]} {selected.year}"
                return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

            missing = date(year or periods[-1].year, month, 1)
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = missing.isoformat()
            period_data["to"] = month_end(missing).isoformat()
            period_data["label"] = f"срез остатков: {MONTH_LABELS[missing.month]} {missing.year}"
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

        selected = periods[-1]
        period_data = frame.period.model_dump(by_alias=True)
        period_data["from"] = selected.isoformat()
        period_data["to"] = month_end(selected).isoformat()
        period_data["label"] = f"последний актуальный срез остатков: {MONTH_LABELS[selected.month]} {selected.year}"
        return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

    def resolve_stock_for_sale_period(self, frame: QueryFrame) -> DomainResolution:
        if frame.intent == "dimension_query" and frame.dimension in {"snapshot_month", "period_month"}:
            return DomainResolution(valid=True, frame=frame)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date is None and to_date is None:
            return DomainResolution(valid=True, frame=frame)

        from_month = month_start(from_date) if from_date else None
        to_month = month_start(to_date) if to_date else None
        periods = self.load_stock_for_sale_periods(frame)
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
            errors=["stock_snapshot_not_found"],
            clarification_question=f"За указанный срез остатков в продаже нет данных. Доступные срезы: {format_periods(periods)}.",
        )

    def resolve_stock_for_sale(self, frame: QueryFrame) -> DomainResolution:
        project_resolution = self.resolve_stock_for_sale_project(frame)
        if not project_resolution.valid:
            return project_resolution
        normalized_frame = self.normalize_stock_for_sale_period(project_resolution.frame)
        return self.resolve_stock_for_sale_period(normalized_frame)
