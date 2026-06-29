from app.llm.parser import LLMParsedResponse
from app.reports.agents_report.corrections import build_agents_report_correction
from app.reports.debt_and_bookings.corrections import build_debt_and_bookings_correction
from app.reports.model.corrections import (
    build_model_available_metrics_correction,
    build_model_comparison_correction,
    build_failed_model_metric_correction,
    build_model_metric_correction,
    build_model_period_summary_correction,
    build_model_raw_rows_correction,
    build_model_raw_sheet_list_correction,
    build_model_sensitive_correction,
    build_model_snapshot_correction,
    build_model_summary_correction,
    build_model_total_area_correction,
)
from app.reports.payment_calendar.corrections import (
    build_article_filter_request_correction,
    build_failed_article_correction,
    build_failed_group_by_correction,
    build_failed_metric_correction,
    build_payment_calendar_view_correction,
    build_unsupported_group_by_request_correction,
    build_unsupported_metric_request_correction,
)
from app.reports.roadmap.corrections import (
    build_explicit_roadmap_sensitive_correction,
    build_explicit_roadmap_unsupported_metric_correction,
    build_failed_roadmap_correction,
    build_roadmap_context_correction,
)
from app.reports.sales_plan_execution.corrections import build_sales_plan_execution_correction
from app.reports.sales_report.corrections import build_sales_report_correction
from app.reports.stock_for_sale.corrections import build_stock_for_sale_correction
from app.reports.summary.corrections import build_summary_correction


def build_forced_parsed_response(
    current_state: dict[str, object],
    text: str | None,
) -> tuple[dict[str, object], LLMParsedResponse | None]:
    forced_parsed_response: LLMParsedResponse | None = None
    model_context = current_state.get("report_type") == "model"
    model_fallback_period = current_state.get("period") if isinstance(current_state.get("period"), dict) else None
    model_available_metrics_correction = build_model_available_metrics_correction(text, model_context=model_context)
    model_sensitive_correction = build_model_sensitive_correction(text)
    model_raw_sheet_list_correction = build_model_raw_sheet_list_correction(text, model_context=model_context)
    model_raw_rows_correction = build_model_raw_rows_correction(text, model_context=model_context)
    model_snapshot_correction = build_model_snapshot_correction(text)
    model_total_area_correction = build_model_total_area_correction(text)
    model_metric_correction = build_model_metric_correction(
        text,
        model_context=model_context,
        fallback_period=model_fallback_period,
    )
    model_comparison_correction = build_model_comparison_correction(text)
    model_period_summary_correction = build_model_period_summary_correction(text)
    model_summary_correction = build_model_summary_correction(text)
    failed_model_metric_correction = build_failed_model_metric_correction(current_state, text)
    unsupported_payment_calendar_metric_correction = build_unsupported_metric_request_correction(text)
    unsupported_payment_calendar_group_by_correction = build_unsupported_group_by_request_correction(text)
    payment_calendar_context = current_state.get("report_type") == "payment_calendar" and current_state.get("awaiting_clarification") is not True
    payment_calendar_article_filter_correction = build_article_filter_request_correction(
        text,
        payment_calendar_context=payment_calendar_context,
    )
    payment_calendar_view_correction = build_payment_calendar_view_correction(
        text,
        payment_calendar_context=payment_calendar_context,
    )
    failed_group_by_correction = build_failed_group_by_correction(current_state, text)
    failed_metric_correction = build_failed_metric_correction(current_state, text)
    failed_article_correction = build_failed_article_correction(current_state, text)
    explicit_roadmap_sensitive_correction = build_explicit_roadmap_sensitive_correction(text)
    explicit_roadmap_unsupported_metric_correction = build_explicit_roadmap_unsupported_metric_correction(text)
    failed_roadmap_correction = build_failed_roadmap_correction(current_state, text)
    roadmap_context_correction = build_roadmap_context_correction(current_state, text)
    debt_and_bookings_correction = build_debt_and_bookings_correction(text)
    stock_for_sale_correction = build_stock_for_sale_correction(text)
    sales_report_correction = build_sales_report_correction(text)
    sales_plan_execution_correction = build_sales_plan_execution_correction(text)
    agents_report_correction = build_agents_report_correction(text)
    summary_correction = build_summary_correction(text)
    agents_report_context = current_state.get("report_type") == "agents_report"
    if model_available_metrics_correction is not None:
        forced_parsed_response = model_available_metrics_correction
    elif model_sensitive_correction is not None:
        forced_parsed_response = model_sensitive_correction
    elif model_raw_sheet_list_correction is not None:
        forced_parsed_response = model_raw_sheet_list_correction
    elif model_raw_rows_correction is not None:
        forced_parsed_response = model_raw_rows_correction
    elif model_snapshot_correction is not None:
        forced_parsed_response = model_snapshot_correction
    elif model_total_area_correction is not None:
        forced_parsed_response = model_total_area_correction
    elif unsupported_payment_calendar_metric_correction is not None:
        forced_parsed_response = unsupported_payment_calendar_metric_correction
    elif model_metric_correction is not None:
        forced_parsed_response = model_metric_correction
    elif model_comparison_correction is not None:
        forced_parsed_response = model_comparison_correction
    elif model_period_summary_correction is not None:
        forced_parsed_response = model_period_summary_correction
    elif model_summary_correction is not None:
        forced_parsed_response = model_summary_correction
    elif failed_model_metric_correction is not None:
        current_state, forced_parsed_response = failed_model_metric_correction
    elif unsupported_payment_calendar_group_by_correction is not None:
        forced_parsed_response = unsupported_payment_calendar_group_by_correction
    elif payment_calendar_article_filter_correction is not None:
        forced_parsed_response = payment_calendar_article_filter_correction
    elif payment_calendar_view_correction is not None:
        forced_parsed_response = payment_calendar_view_correction
    elif explicit_roadmap_sensitive_correction is not None:
        forced_parsed_response = explicit_roadmap_sensitive_correction
    elif explicit_roadmap_unsupported_metric_correction is not None:
        forced_parsed_response = explicit_roadmap_unsupported_metric_correction
    elif debt_and_bookings_correction is not None:
        forced_parsed_response = debt_and_bookings_correction
    elif agents_report_context and agents_report_correction is not None:
        forced_parsed_response = agents_report_correction
    elif stock_for_sale_correction is not None:
        forced_parsed_response = stock_for_sale_correction
    elif sales_report_correction is not None:
        forced_parsed_response = sales_report_correction
    elif sales_plan_execution_correction is not None:
        forced_parsed_response = sales_plan_execution_correction
    elif agents_report_correction is not None:
        forced_parsed_response = agents_report_correction
    elif summary_correction is not None:
        forced_parsed_response = summary_correction
    elif failed_group_by_correction is not None:
        current_state, forced_parsed_response = failed_group_by_correction
    elif failed_metric_correction is not None:
        current_state, forced_parsed_response = failed_metric_correction
    elif failed_article_correction is not None:
        current_state, forced_parsed_response = failed_article_correction
    elif failed_roadmap_correction is not None:
        current_state, forced_parsed_response = failed_roadmap_correction
    elif roadmap_context_correction is not None:
        forced_parsed_response = roadmap_context_correction
    return current_state, forced_parsed_response
