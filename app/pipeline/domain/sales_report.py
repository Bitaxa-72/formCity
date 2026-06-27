from app.pipeline.domain.common import *


class SalesReportDomainMixin:
    def load_sales_report_projects(self) -> list[str]:
        statement = select(SalesReportSource.project).distinct().order_by(SalesReportSource.project)
        return list(self.db.execute(statement).scalars().all())

    def load_sales_report_snapshots(self, frame: QueryFrame) -> list[date]:
        statement = select(SalesReportSource.snapshot_month).distinct()
        if frame.project and frame.project != "all":
            statement = statement.where(SalesReportSource.project == frame.project)
        return list(self.db.execute(statement.order_by(SalesReportSource.snapshot_month)).scalars().all())

    def load_sales_report_periods(self, frame: QueryFrame) -> list[date]:
        statement = select(SalesReportFact.period_month).distinct().where(SalesReportFact.period_month.is_not(None))
        if frame.project and frame.project != "all":
            statement = statement.where(SalesReportFact.project == frame.project)
        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date:
            statement = statement.where(SalesReportFact.snapshot_month >= month_start(from_date))
        if to_date:
            statement = statement.where(SalesReportFact.snapshot_month <= month_start(to_date))
        return list(self.db.execute(statement.order_by(SalesReportFact.period_month)).scalars().all())

    def resolve_sales_report_project(self, frame: QueryFrame) -> DomainResolution:
        project = frame.project or "obvodny"
        projects = self.load_sales_report_projects()
        if project == "all":
            project = "obvodny"
        if project in projects:
            return DomainResolution(valid=True, frame=frame.model_copy(update={"project": project}))
        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["project_data_not_found"],
            clarification_question=f"По проекту {PROJECT_LIST_LABELS.get(project, project)} отчет о продажах пока не загружен. Доступные проекты: {format_project_list(projects)}.",
        )

    def normalize_sales_report_snapshot(self, frame: QueryFrame) -> QueryFrame:
        snapshots = self.load_sales_report_snapshots(frame)
        if not snapshots:
            return frame

        if frame.intent == "dimension_query":
            return frame

        period_range = period_range_from_label(frame.period.label, snapshots)
        if period_range:
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = period_range[0].isoformat()
            period_data["to"] = period_range[1].isoformat()
            return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

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
                period_data["label"] = f"срез отчета о продажах: {MONTH_LABELS[selected.month]} {selected.year}"
                return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

            missing = date(year or snapshots[-1].year, month, 1)
            period_data = frame.period.model_dump(by_alias=True)
            period_data["from"] = missing.isoformat()
            period_data["to"] = month_end(missing).isoformat()
            period_data["label"] = f"срез отчета о продажах: {MONTH_LABELS[missing.month]} {missing.year}"
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
        period_data["label"] = f"последний актуальный срез продаж: {MONTH_LABELS[selected.month]} {selected.year}"
        return frame.model_copy(update={"period": QueryPeriod.model_validate(period_data)})

    def resolve_sales_report_snapshot(self, frame: QueryFrame) -> DomainResolution:
        if frame.intent == "dimension_query":
            return DomainResolution(valid=True, frame=frame)

        from_date = parse_iso_date(frame.period.from_date)
        to_date = parse_iso_date(frame.period.to)
        if from_date is None and to_date is None:
            return DomainResolution(valid=True, frame=frame)

        from_month = month_start(from_date) if from_date else None
        to_month = month_start(to_date) if to_date else None
        snapshots = self.load_sales_report_snapshots(frame)
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
            errors=["sales_snapshot_not_found"],
            clarification_question=f"За указанный срез отчета о продажах нет данных. Доступные срезы: {format_periods(snapshots)}.",
        )

    def resolve_sales_report_period_month(self, frame: QueryFrame) -> DomainResolution:
        value = frame.filters.get("period_month")
        if not isinstance(value, str):
            return DomainResolution(valid=True, frame=frame)

        requested = parse_iso_date(value)
        if requested is None:
            return DomainResolution(valid=True, frame=frame)

        requested_month = month_start(requested)
        periods = self.load_sales_report_periods(frame)
        if requested_month in periods:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["sales_period_month_not_found"],
            clarification_question=f"За указанный месяц продаж нет данных. Доступные месяцы продаж: {format_periods(periods)}.",
        )

    def resolve_sales_report(self, frame: QueryFrame) -> DomainResolution:
        project_resolution = self.resolve_sales_report_project(frame)
        if not project_resolution.valid:
            return project_resolution
        normalized_frame = self.normalize_sales_report_snapshot(project_resolution.frame)
        snapshot_resolution = self.resolve_sales_report_snapshot(normalized_frame)
        if not snapshot_resolution.valid:
            return snapshot_resolution
        return self.resolve_sales_report_period_month(snapshot_resolution.frame)
