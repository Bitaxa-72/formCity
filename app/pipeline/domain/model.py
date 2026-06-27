from app.pipeline.domain.common import *


class ModelDomainMixin:
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
