from sqlalchemy.orm import Session

from app.pipeline.query_frame import QueryFrame
from app.pipeline.domain.common import *
from app.pipeline.domain.payment_calendar import PaymentCalendarDomainMixin
from app.pipeline.domain.roadmap import RoadmapDomainMixin
from app.pipeline.domain.non_project_expenses import NonProjectExpensesDomainMixin
from app.pipeline.domain.stock_for_sale import StockForSaleDomainMixin
from app.pipeline.domain.sales_report import SalesReportDomainMixin
from app.pipeline.domain.sales_plan_execution import SalesPlanExecutionDomainMixin
from app.pipeline.domain.agents_report import AgentsReportDomainMixin
from app.pipeline.domain.summary import SummaryDomainMixin
from app.pipeline.domain.model import ModelDomainMixin


class DomainResolver(ModelDomainMixin, SummaryDomainMixin, AgentsReportDomainMixin, SalesPlanExecutionDomainMixin, SalesReportDomainMixin, StockForSaleDomainMixin, NonProjectExpensesDomainMixin, RoadmapDomainMixin, PaymentCalendarDomainMixin):
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(self, frame: QueryFrame) -> DomainResolution:
        if not frame.ready:
            return DomainResolution(valid=True, frame=frame)
        if frame.report_type == "model":
            return self.resolve_model(frame)
        if frame.report_type == "non_project_expenses":
            return self.resolve_non_project_expenses(frame)
        if frame.report_type == "stock_for_sale":
            return self.resolve_stock_for_sale(frame)
        if frame.report_type == "sales_report":
            return self.resolve_sales_report(frame)
        if frame.report_type == "sales_plan_execution":
            return self.resolve_sales_plan_execution(frame)
        if frame.report_type == "agents_report":
            return self.resolve_agents_report(frame)
        if frame.report_type == "summary":
            return self.resolve_summary_project(frame)
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
