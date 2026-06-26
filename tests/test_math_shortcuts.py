from app.pipeline.math_shortcuts import (
    MATH_AMBIGUOUS_VALUE_MESSAGE,
    PERCENT_DEVIATION_NOT_ENOUGH_DATA_MESSAGE,
    resolve_math_shortcut,
)


def test_resolve_math_shortcut_divides_single_last_value() -> None:
    result = resolve_math_shortcut(
        "подели на 2",
        {"rows": [{"plan": 6170978}], "metrics": ["plan"]},
    )

    assert result.handled is True
    assert result.text == "Результат: 3 085 489 руб."
    assert result.result is not None
    assert result.result.rows == [{"value": 3085489.0}]


def test_resolve_math_shortcut_ignores_source_rows_when_metric_is_known() -> None:
    result = resolve_math_shortcut(
        "подели на 2",
        {"rows": [{"plan": 6170978, "source_rows": 1}], "metrics": ["plan"]},
    )

    assert result.handled is True
    assert result.text == "Результат: 3 085 489 руб."
    assert result.result is not None
    assert result.result.rows == [{"value": 3085489.0}]


def test_resolve_math_shortcut_multiplies_word_number() -> None:
    result = resolve_math_shortcut(
        "умножь на десять",
        {"rows": [{"value": 12}], "metrics": ["value"]},
    )

    assert result.handled is True
    assert result.text == "Результат: 120 руб."


def test_resolve_math_shortcut_adds_thousand_marker() -> None:
    result = resolve_math_shortcut(
        "прибавь 100 тыс",
        {"rows": [{"fact": 50}], "metrics": ["fact"]},
    )

    assert result.handled is True
    assert result.text == "Результат: 100 050 руб."


def test_resolve_math_shortcut_rejects_ambiguous_last_result() -> None:
    result = resolve_math_shortcut(
        "подели на 2",
        {"rows": [{"plan": 100, "fact": 90}], "metrics": ["plan", "fact"]},
    )

    assert result.handled is True
    assert result.text == MATH_AMBIGUOUS_VALUE_MESSAGE
    assert result.result is None


def test_resolve_math_shortcut_calculates_percent_deviation_from_plan_and_fact() -> None:
    result = resolve_math_shortcut(
        "какое отклонение в процентах?",
        {"rows": [{"plan": 100, "fact": 80}], "metrics": ["plan", "fact"]},
    )

    assert result.handled is True
    assert result.text == "Отклонение: -20%"
    assert result.result is not None
    assert result.result.rows == [{"value": -20.0}]


def test_resolve_math_shortcut_explains_missing_percent_data() -> None:
    result = resolve_math_shortcut(
        "какое отклонение в процентах?",
        {"rows": [{"plan": 100}], "metrics": ["plan"]},
    )

    assert result.handled is True
    assert result.text == PERCENT_DEVIATION_NOT_ENOUGH_DATA_MESSAGE
    assert result.result is None
