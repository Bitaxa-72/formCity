from app.llm.schema import Dimension, GroupBy, Intent, Metric, OperationSource, OperationType, PaymentCalendarView, Project, ReportType
from app.llm.report_rules import REPORT_RULES, REPORT_TYPE_ALIASES


def build_llm_dictionary() -> dict[str, object]:
    return {
        "intent": [item.value for item in Intent],
        "report_type": [item.value for item in ReportType],
        "report_type_aliases": REPORT_TYPE_ALIASES,
        "report_rules": REPORT_RULES,
        "project": [item.value for item in Project],
        "metric": [item.value for item in Metric],
        "payment_calendar_view": [
            PaymentCalendarView.SUMMARY.value,
            PaymentCalendarView.DETAILS.value,
            PaymentCalendarView.PAYMENTS.value,
            PaymentCalendarView.INCOME.value,
            PaymentCalendarView.BALANCE_START.value,
            PaymentCalendarView.BALANCE_END.value,
        ],
        "report_view": [item.value for item in PaymentCalendarView],
        "dimension": [item.value for item in Dimension],
        "group_by": [item.value for item in GroupBy],
        "operation_type": [item.value for item in OperationType],
        "operation_source": [item.value for item in OperationSource],
    }
