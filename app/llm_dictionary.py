from enum import StrEnum


class Intent(StrEnum):
    DATA_QUERY = "data_query"
    CONTEXT_QUERY = "context_query"
    MATH_ON_LAST_RESULT = "math_on_last_result"
    CLARIFICATION_ANSWER = "clarification_answer"
    GENERAL_QUESTION = "general_question"
    UNSUPPORTED = "unsupported"


class ReportType(StrEnum):
    SUMMARY = "summary"
    MODEL = "model"
    PAYMENT_CALENDAR = "payment_calendar"
    ROADMAP = "roadmap"
    SALES_REPORT = "sales_report"
    SALES_PLAN_EXECUTION = "sales_plan_execution"
    AGENTS_REPORT = "agents_report"
    STOCK_FOR_SALE = "stock_for_sale"
    DEBT_AND_BOOKINGS = "debt_and_bookings"
    NON_PROJECT_EXPENSES = "non_project_expenses"
    UNKNOWN = "unknown"


class Project(StrEnum):
    OBVODNY_118 = "obvodny_118"
    WELL_MOSKOVSKY = "well_moskovsky"
    EVGENIEVSKY = "evgenievsky"
    ALL = "all"
    UNKNOWN = "unknown"


class Metric(StrEnum):
    REVENUE = "revenue"
    SOLD_AREA = "sold_area"
    DEAL_COUNT = "deal_count"
    AVERAGE_DEAL_PRICE = "average_deal_price"
    PRICE_PER_SQUARE_METER = "price_per_square_meter"
    DEBT = "debt"
    BOOKING_AMOUNT = "booking_amount"
    PLAN = "plan"
    FACT = "fact"
    DEVIATION = "deviation"
    AGENT_COMMISSION = "agent_commission"
    PLEDGE_RELEASE_AMOUNT = "pledge_release_amount"
    REMAINING_AMOUNT = "remaining_amount"
    UNKNOWN = "unknown"


class GroupBy(StrEnum):
    PROJECT = "project"
    PERIOD = "period"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    FLOOR = "floor"
    ROOM_TYPE = "room_type"
    AGENT = "agent"
    BANK = "bank"
    METRIC = "metric"


class OperationType(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    PERCENT = "percent"
    DIFFERENCE = "difference"
    RATIO = "ratio"
    AVERAGE = "average"
    COMPARE_PERIODS = "compare_periods"
    SAME_METRIC_OTHER_PERIOD = "same_metric_other_period"


class OperationSource(StrEnum):
    LAST_RESULT = "last_result"
    DIALOG_STATE = "dialog_state"
    LITERAL = "literal"
