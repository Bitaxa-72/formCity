from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


DEBT_AND_BOOKINGS_FACTS_TABLE_SQL = """
(
    SELECT
        project,
        snapshot_month,
        snapshot_date,
        NULL AS period_month,
        'items' AS source_kind,
        item_kind,
        row_type,
        section,
        unit_number,
        NULL AS status,
        NULL AS payment_type,
        1 AS item_count,
        total_amount,
        NULL AS monthly_value,
        NULL AS plan_amount,
        NULL AS updated_plan_amount,
        NULL AS fact_payment_amount,
        NULL AS remaining_amount,
        0 AS refusal_count,
        NULL AS refusal_area,
        NULL AS refusal_full_price
    FROM debt_booking_items
    UNION ALL
    SELECT
        m.project,
        m.snapshot_month,
        m.snapshot_date,
        m.period_month,
        'monthly' AS source_kind,
        m.item_kind,
        m.row_type,
        NULL AS section,
        i.unit_number AS unit_number,
        NULL AS status,
        NULL AS payment_type,
        0 AS item_count,
        NULL AS total_amount,
        m.value AS monthly_value,
        NULL AS plan_amount,
        NULL AS updated_plan_amount,
        NULL AS fact_payment_amount,
        NULL AS remaining_amount,
        0 AS refusal_count,
        NULL AS refusal_area,
        NULL AS refusal_full_price
    FROM debt_booking_monthly_values m
    LEFT JOIN debt_booking_items i
        ON i.project = m.project
        AND i.snapshot_date = m.snapshot_date
        AND i.source_row = m.item_source_row
        AND i.source_sheet = m.source_sheet
        AND COALESCE(i.source_file, '') = COALESCE(m.source_file, '')
    UNION ALL
    SELECT
        project,
        snapshot_month,
        snapshot_date,
        period_month,
        'deviations' AS source_kind,
        item_kind,
        row_type,
        section,
        unit_number,
        NULL AS status,
        NULL AS payment_type,
        0 AS item_count,
        NULL AS total_amount,
        NULL AS monthly_value,
        plan_amount,
        updated_plan_amount,
        fact_payment_amount,
        remaining_amount,
        0 AS refusal_count,
        NULL AS refusal_area,
        NULL AS refusal_full_price
    FROM debt_booking_deviations
    UNION ALL
    SELECT
        project,
        snapshot_month,
        snapshot_date,
        NULL AS period_month,
        'refusals' AS source_kind,
        'refusal' AS item_kind,
        'detail' AS row_type,
        NULL AS section,
        unit_number,
        status,
        payment_type,
        0 AS item_count,
        NULL AS total_amount,
        NULL AS monthly_value,
        NULL AS plan_amount,
        NULL AS updated_plan_amount,
        NULL AS fact_payment_amount,
        NULL AS remaining_amount,
        1 AS refusal_count,
        area_sqm AS refusal_area,
        full_price_amount AS refusal_full_price
    FROM debt_booking_refusals
) AS debt_and_bookings_facts
""".strip()

DEBT_AND_BOOKINGS_GROUP_BY_COLUMNS = {
    "month": "snapshot_month",
    "period": "period_month",
    "period_month": "period_month",
    "snapshot_month": "snapshot_month",
    "source_kind": "source_kind",
    "item_kind": "item_kind",
    "row_type": "row_type",
    "section": "section",
    "unit_number": "unit_number",
    "status": "status",
    "payment_type": "payment_type",
}

DEBT_AND_BOOKINGS_FILTER_COLUMNS = {
    "snapshot_month": "snapshot_month",
    "snapshot_date": "snapshot_date",
    "period_month": "period_month",
    "source_kind": "source_kind",
    "item_kind": "item_kind",
    "row_type": "row_type",
    "section": "section",
    "section_contains": "section",
    "unit_number": "unit_number",
    "unit_number_contains": "unit_number",
    "unit_number_not_null": "unit_number",
    "status": "status",
    "payment_type": "payment_type",
}

DEBT_AND_BOOKINGS_DIMENSION_COLUMNS = {
    "period_month": "snapshot_month",
    "period": "snapshot_month",
    "month": "snapshot_month",
    "snapshot_month": "snapshot_month",
    "source_kind": "source_kind",
    "item_kind": "item_kind",
    "row_type": "row_type",
    "section": "section",
    "unit_number": "unit_number",
    "status": "status",
    "payment_type": "payment_type",
}


DEBT_AND_BOOKINGS_SQL_TEMPLATE = ReportSQLTemplate(
    table=DEBT_AND_BOOKINGS_FACTS_TABLE_SQL,
    date_column="snapshot_month",
    project_column="project",
    metrics={
        "debt_item_count": MetricSQLSpec("SUM(item_count)", "debt_item_count"),
        "debt_total_amount": MetricSQLSpec("SUM(total_amount)", "debt_total_amount"),
        "debt_monthly_value": MetricSQLSpec("SUM(monthly_value)", "debt_monthly_value"),
        "debt_plan_amount": MetricSQLSpec("SUM(plan_amount)", "debt_plan_amount"),
        "debt_updated_plan_amount": MetricSQLSpec("SUM(updated_plan_amount)", "debt_updated_plan_amount"),
        "debt_fact_payment_amount": MetricSQLSpec("SUM(fact_payment_amount)", "debt_fact_payment_amount"),
        "debt_remaining_amount": MetricSQLSpec("SUM(remaining_amount)", "debt_remaining_amount"),
        "debt_refusal_count": MetricSQLSpec("SUM(refusal_count)", "debt_refusal_count"),
        "debt_refusal_area": MetricSQLSpec("SUM(refusal_area)", "debt_refusal_area"),
        "debt_refusal_full_price": MetricSQLSpec("SUM(refusal_full_price)", "debt_refusal_full_price"),
    },
    group_by_columns=DEBT_AND_BOOKINGS_GROUP_BY_COLUMNS,
    filter_columns=DEBT_AND_BOOKINGS_FILTER_COLUMNS,
    dimension_columns=DEBT_AND_BOOKINGS_DIMENSION_COLUMNS,
)
