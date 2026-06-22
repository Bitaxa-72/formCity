import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.calculation_engine import CalculationError, calculate_operation, execute_sql_query
from app.sql_compiler import SQLQuery


def create_session():
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_factory()


def test_execute_sql_query_returns_normalized_rows() -> None:
    db = create_session()
    db.execute(
        text(
            "CREATE TABLE sales_facts ("
            "project TEXT, "
            "revenue_amount REAL, "
            "deal_id INTEGER"
            ")",
        ),
    )
    db.execute(
        text(
            "INSERT INTO sales_facts (project, revenue_amount, deal_id) "
            "VALUES ('obvodny_118', 100.126, 1), ('obvodny_118', 50.129, 2)",
        ),
    )
    db.commit()
    sql_query = SQLQuery(
        sql=(
            "SELECT project AS project, "
            "SUM(revenue_amount) AS revenue, "
            "COUNT(deal_id) AS deal_count "
            "FROM sales_facts "
            "WHERE project = :project "
            "GROUP BY project"
        ),
        params={"project": "obvodny_118"},
        table="sales_facts",
        metrics=["revenue", "deal_count"],
        group_by=["project"],
    )

    result = execute_sql_query(db, sql_query)

    assert result.kind == "sql_result"
    assert result.row_count == 1
    assert result.columns == ["project", "revenue", "deal_count"]
    assert result.rows == [
        {
            "project": "obvodny_118",
            "revenue": 150.26,
            "deal_count": 2,
        },
    ]


def test_execute_sql_query_wraps_sql_errors() -> None:
    db = create_session()
    sql_query = SQLQuery(
        sql="SELECT value FROM missing_table",
        params={},
        table="missing_table",
        metrics=["value"],
        group_by=[],
    )

    with pytest.raises(CalculationError, match="sql_execution_failed"):
        execute_sql_query(db, sql_query)


def test_calculate_operation_divides_last_result_metric() -> None:
    result = calculate_operation(
        {
            "type": "divide",
            "left": {"source": "last_result", "metric": "revenue"},
            "right": {"source": "literal", "value": 2},
        },
        {
            "rows": [
                {
                    "revenue": 101.555,
                },
            ],
        },
    )

    assert result.kind == "operation_result"
    assert result.rows == [{"value": 50.78}]
    assert result.operation is not None


def test_calculate_operation_rejects_division_by_zero() -> None:
    with pytest.raises(CalculationError, match="division_by_zero"):
        calculate_operation(
            {
                "type": "divide",
                "left": {"source": "literal", "value": 100},
                "right": {"source": "literal", "value": 0},
            },
            None,
        )
