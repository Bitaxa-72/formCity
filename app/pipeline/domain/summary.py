from app.pipeline.domain.common import *


class SummaryDomainMixin:
    def load_summary_projects(self) -> list[str]:
        statement = select(SummarySource.project).distinct().order_by(SummarySource.project)
        return list(self.db.execute(statement).scalars().all())

    def resolve_summary_project(self, frame: QueryFrame) -> DomainResolution:
        if not frame.project or frame.project == "all":
            return DomainResolution(valid=True, frame=frame)

        projects = self.load_summary_projects()
        if frame.project in projects:
            return DomainResolution(valid=True, frame=frame)

        return DomainResolution(
            valid=False,
            frame=frame,
            errors=["project_data_not_found"],
            clarification_question=f"По проекту {PROJECT_LIST_LABELS.get(frame.project, frame.project)} сводный отчет пока не загружен. Доступные проекты: {format_project_list(projects)}.",
        )
