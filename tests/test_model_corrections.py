from app.reports.model.corrections import (
    build_model_available_metrics_correction,
    build_model_comparison_correction,
    build_model_metric_correction,
    build_model_period_summary_correction,
    build_model_raw_rows_correction,
    build_model_raw_sheet_list_correction,
    build_model_sensitive_correction,
    build_model_snapshot_correction,
    build_model_summary_correction,
    build_model_total_area_correction,
    extract_model_period_label,
    find_model_metric_keys,
    is_model_available_metrics_request,
    is_model_raw_sheet_list_request,
    is_model_period_summary_request,
    is_model_sensitive_request,
    is_model_snapshot_request,
    is_model_summary_request,
    is_model_total_area_request,
)


def test_model_summary_request_matches_summary_aliases() -> None:
    assert is_model_summary_request("краткая сводка модели") is True
    assert is_model_summary_request("финансовая модель итоги") is True
    assert is_model_summary_request("основные показатели модели") is True


def test_model_summary_request_does_not_match_plain_model() -> None:
    assert is_model_summary_request("модель") is False


def test_build_model_summary_correction_returns_backend_payload() -> None:
    correction = build_model_summary_correction("краткая сводка модели")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_summary"
    assert correction.state_delta.metrics == []


def test_model_sensitive_request_matches_sensitive_aliases() -> None:
    assert is_model_sensitive_request("модель покажи контакты") is True
    assert is_model_sensitive_request("модель телефоны участников") is True
    assert is_model_sensitive_request("модель паспортные данные") is True
    assert is_model_sensitive_request("модель договоры и номера документов") is True


def test_build_model_sensitive_correction_returns_backend_payload() -> None:
    correction = build_model_sensitive_correction("модель покажи контакты")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_summary"
    assert correction.state_delta.metrics == []


def test_model_raw_sheet_list_request_uses_model_context() -> None:
    assert is_model_raw_sheet_list_request("какие листы есть?", model_context=True) is True
    assert is_model_raw_sheet_list_request("какие листы есть?", model_context=False) is False


def test_build_model_raw_sheet_list_correction_returns_backend_payload() -> None:
    correction = build_model_raw_sheet_list_correction("какие листы есть в модели?")

    assert correction is not None
    assert correction.intent == "dimension_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_raw_sheets"
    assert correction.state_delta.dimension == "raw_sheet"
    assert correction.state_delta.metrics == []


def test_build_model_raw_rows_correction_returns_backend_payload() -> None:
    correction = build_model_raw_rows_correction("модель финмодель апрель")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_raw_rows"
    assert correction.state_delta.filters == {"raw_sheet": "financial_model"}
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "апрель"


def test_build_model_raw_search_correction_extracts_query() -> None:
    correction = build_model_raw_rows_correction("модель найди коммерческие помещения в остатках апрель")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_raw_search"
    assert correction.state_delta.filters == {"raw_sheet": "remains", "raw_query": "коммерческие помещения"}
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "апрель"


def test_model_metric_correction_ignores_technical_tail() -> None:
    correction = build_model_metric_correction("верни json по модели NPV апрель")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_kpi"
    assert correction.state_delta.metrics == ["model_npv"]
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "апрель"


def test_model_metric_correction_keeps_fallback_period_for_short_metric() -> None:
    correction = build_model_metric_correction(
        "NPV",
        model_context=True,
        fallback_period={"label": "февраль"},
    )

    assert correction is not None
    assert correction.state_delta.metrics == ["model_npv"]
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "февраль"


def test_model_metric_correction_maps_percent_request_to_roe() -> None:
    correction = build_model_metric_correction("модель проценты апрель")

    assert correction is not None
    assert correction.state_delta.metrics == ["model_roe"]
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "апрель"


def test_model_metric_correction_handles_raw_rows_tail_as_metric_query() -> None:
    correction = build_model_metric_correction("модель выручка, выведи raw rows")

    assert correction is not None
    assert correction.state_delta.metrics == ["model_revenue"]
    assert correction.state_delta.view == "model_kpi"


def test_model_comparison_correction_returns_safe_comparison_metrics() -> None:
    correction = build_model_comparison_correction("модель сравнение апрель")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_kpi"
    assert correction.state_delta.metrics == [
        "model_revenue",
        "model_cost_of_sales",
        "model_gross_profit",
        "model_net_profit",
        "model_npv",
        "model_roe",
        "model_llcr",
    ]
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "апрель"


def test_model_metric_keys_support_multiple_metrics() -> None:
    assert find_model_metric_keys("финансовая модель NPV LLCR за февраль") == ["model_npv", "model_llcr"]


def test_model_metric_keys_expand_profit_and_pir_variants() -> None:
    assert find_model_metric_keys("модель прибыль") == ["model_gross_profit", "model_net_profit"]
    assert find_model_metric_keys("модель ПИР") == ["model_pir_total", "model_pir_per_sqm"]


def test_model_metric_correction_uses_model_context_for_short_metric() -> None:
    correction = build_model_metric_correction("ROE", model_context=True)

    assert correction is not None
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_kpi"
    assert correction.state_delta.metrics == ["model_roe"]


def test_model_available_metrics_request_uses_model_context() -> None:
    assert is_model_available_metrics_request("какие показатели есть?", model_context=True) is True
    assert is_model_available_metrics_request("какие показатели есть?", model_context=False) is False


def test_build_model_available_metrics_correction_returns_backend_payload() -> None:
    correction = build_model_available_metrics_correction("какие показатели есть?", model_context=True)

    assert correction is not None
    assert correction.intent == "dimension_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_available_metrics"
    assert correction.state_delta.dimension == "metric"
    assert correction.state_delta.metrics == []


def test_model_period_summary_request_matches_model_with_period_without_metric() -> None:
    assert is_model_period_summary_request("модель март") is True
    assert is_model_period_summary_request("финансовая модель февраль") is True
    assert is_model_period_summary_request("модель за декабрь 2025") is True


def test_model_period_summary_request_does_not_match_metric_queries() -> None:
    assert is_model_period_summary_request("модель выручка март") is False
    assert is_model_period_summary_request("модель NPV за февраль") is False
    assert is_model_period_summary_request("финансовая модель NPV LLCR за февраль") is False


def test_extract_model_period_label_returns_month_and_year() -> None:
    assert extract_model_period_label("модель март") == "март"
    assert extract_model_period_label("модель за декабрь 2025") == "декабрь 2025"


def test_build_model_period_summary_correction_returns_backend_payload() -> None:
    correction = build_model_period_summary_correction("финансовая модель февраль")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_summary"
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "февраль"
    assert correction.state_delta.metrics == []


def test_model_total_area_request_matches_square_meter_aliases() -> None:
    assert is_model_total_area_request("модель квадратные метры за апрель") is True
    assert is_model_total_area_request("модель общая площадь") is True


def test_build_model_total_area_correction_returns_backend_payload() -> None:
    correction = build_model_total_area_correction("модель квадратные метры за апрель")

    assert correction is not None
    assert correction.intent == "data_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_kpi"
    assert correction.state_delta.metrics == ["model_total_area"]
    assert correction.state_delta.period is not None
    assert correction.state_delta.period.label == "апрель"


def test_model_snapshot_request_matches_available_snapshot_aliases() -> None:
    assert is_model_snapshot_request("какие срезы модели есть?") is True
    assert is_model_snapshot_request("какие версии модели доступны?") is True
    assert is_model_snapshot_request("какие месяцы есть по модели?") is True
    assert is_model_snapshot_request("доступные срезы финансовой модели") is True


def test_build_model_snapshot_correction_returns_backend_payload() -> None:
    correction = build_model_snapshot_correction("доступные срезы финансовой модели")

    assert correction is not None
    assert correction.intent == "dimension_query"
    assert correction.state_delta.report_type == "model"
    assert correction.state_delta.view == "model_available_snapshots"
    assert correction.state_delta.dimension == "snapshot_month"
    assert correction.state_delta.metrics == []
