from app.pipeline.query_frame import QueryFrame
from app.pipeline.report_compatibility import check_report_compatibility
from app.pipeline.semantic_compatibility import check_semantic_compatibility


def frame(report_type: str, *, metrics: list[str] | None = None, group_by: list[str] | None = None) -> QueryFrame:
    return QueryFrame(
        intent="data_query",
        report_type=report_type,
        project="all",
        period={"label": "май"},
        metrics=metrics or ["summary_value_sum"],
        filters={},
        group_by=group_by or [],
        ready=True,
        missing_fields=[],
    )


def test_semantic_compatibility_rejects_model_with_payment_calendar_article() -> None:
    result = check_semantic_compatibility(
        frame("model", metrics=["model_npv"]),
        "модель план по рекламе апрель",
    )

    assert result.valid is False
    assert result.error == "semantic_term_not_supported_for_report"
    assert 'нет показателя или разреза "реклама"' in result.message
    assert "Доступные отчеты:" in result.message


def test_semantic_compatibility_rejects_roadmap_with_sales_metric() -> None:
    result = check_semantic_compatibility(
        frame("roadmap", metrics=["duration_min"]),
        "дорожная карта выручка апрель",
    )

    assert result.valid is False
    assert result.error == "semantic_term_not_supported_for_report"
    assert 'нет показателя или разреза "выручка"' in result.message


def test_report_compatibility_keeps_specific_model_error_priority() -> None:
    result = check_report_compatibility(
        frame("model", metrics=["model_npv"]),
        "модель план по рекламе апрель",
    )

    assert result.valid is False
    assert result.error == "metric_not_supported_for_model"


def test_semantic_compatibility_rejects_agents_report_with_model_metric() -> None:
    result = check_report_compatibility(
        frame("agents_report", metrics=["agents_deals_count"]),
        "отчет по агентам NPV апрель",
    )

    assert result.valid is False
    assert result.error == "semantic_term_not_supported_for_report"
    assert 'нет показателя или разреза "NPV"' in result.message


def test_semantic_compatibility_allows_supported_sales_metric() -> None:
    result = check_report_compatibility(
        frame("sales_report", metrics=["sales_contract_revenue"]),
        "отчет о продажах выручка апрель",
    )

    assert result.valid is True


def test_semantic_compatibility_does_not_block_non_payment_context_without_explicit_report() -> None:
    result = check_semantic_compatibility(
        frame("roadmap", metrics=["duration_min"]),
        "выручка",
    )

    assert result.valid is True
