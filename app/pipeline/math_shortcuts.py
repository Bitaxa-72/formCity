import re
from dataclasses import dataclass
from typing import Any

from app.pipeline.calculation_engine import CalculationResult, normalize_value
from app.pipeline.domain_resolver import normalize_search_text


MATH_NOT_ENOUGH_CONTEXT_MESSAGE = "Сначала нужен результат, с которым можно выполнить расчет."
MATH_AMBIGUOUS_VALUE_MESSAGE = "В последнем результате несколько чисел. Уточните, какой показатель использовать: план, факт или отклонение."
PERCENT_DEVIATION_NOT_ENOUGH_DATA_MESSAGE = "Для расчета отклонения в процентах нужны план и факт. Сейчас в контексте не хватает данных."

NUMBER_WORDS = {
    "ноль": 0,
    "один": 1,
    "одну": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "сто": 100,
}
METRIC_LABELS = {
    "plan": "План",
    "fact": "Факт",
    "deviation": "Отклонение",
    "value": "Результат",
}
INTERNAL_NUMERIC_COLUMNS = {"source_rows"}


@dataclass(frozen=True)
class MathShortcut:
    handled: bool
    text: str | None = None
    result: CalculationResult | None = None


def format_number(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    if isinstance(value, float):
        formatted = f"{value:,.2f}".replace(",", " ")
        return formatted.rstrip("0").rstrip(".")
    return str(value)


def parse_number(text: str) -> float | None:
    normalized = normalize_search_text(text)
    number_match = re.search(r"\d+(?:[.,]\d+)?", normalized)
    if number_match:
        value = float(number_match.group(0).replace(",", "."))
    else:
        value = next((float(number) for word, number in NUMBER_WORDS.items() if word in normalized.split()), None)

    if value is None:
        return None
    if any(marker in normalized for marker in {"тыс", "тысяч", "тысячи"}):
        value *= 1000
    return value


def numeric_values(last_result: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(last_result, dict):
        return {}

    rows = last_result.get("rows")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        return {}

    metrics = last_result.get("metrics")
    if isinstance(metrics, list):
        metric_values = {
            key: float(rows[0][key])
            for key in metrics
            if isinstance(key, str) and isinstance(rows[0].get(key), int | float)
        }
        if metric_values:
            return metric_values

    values = {}
    for key, value in rows[0].items():
        if key not in INTERNAL_NUMERIC_COLUMNS and isinstance(value, int | float):
            values[key] = float(value)
    return values


def select_value_for_arithmetic(values: dict[str, float], text: str) -> tuple[str, float] | None:
    if not values:
        return None

    normalized = normalize_search_text(text)
    metric_markers = {
        "plan": {"план", "плановый"},
        "fact": {"факт", "фактический"},
        "deviation": {"отклонение", "разница"},
        "value": {"результат", "значение"},
    }
    for metric, markers in metric_markers.items():
        if metric in values and any(marker in normalized for marker in markers):
            return metric, values[metric]

    if len(values) == 1:
        return next(iter(values.items()))
    return None


def detect_arithmetic_operation(text: str) -> str | None:
    normalized = normalize_search_text(text)
    if any(marker in normalized for marker in {"подели", "раздели", "дели", "пополам"}):
        return "divide"
    if any(marker in normalized for marker in {"умнож", "умножь"}):
        return "multiply"
    if any(marker in normalized for marker in {"прибавь", "добавь", "плюс", "увеличь"}):
        return "add"
    if any(marker in normalized for marker in {"вычти", "отними", "минус", "уменьши"}):
        return "subtract"
    return None


def detect_percent_deviation(text: str) -> bool:
    normalized = normalize_search_text(text)
    has_percent = "%" in text or any(marker in normalized for marker in {"процент", "процентах"})
    has_deviation = any(marker in normalized for marker in {"отклон", "отлич", "разниц"})
    return has_percent and has_deviation


def build_result(operation: dict[str, Any], value: float, text: str, unit: str | None = "руб.") -> MathShortcut:
    normalized_value = normalize_value(value)
    suffix = f" {unit}" if unit else ""
    return MathShortcut(
        handled=True,
        text=f"Результат: {format_number(normalized_value)}{suffix}",
        result=CalculationResult(
            kind="operation_result",
            rows=[{"value": normalized_value}],
            row_count=1,
            metrics=["value"],
            columns=["value"],
            operation=operation,
        ),
    )


def resolve_arithmetic_shortcut(text: str, last_result: dict[str, Any] | None) -> MathShortcut:
    operation_type = detect_arithmetic_operation(text)
    if operation_type is None:
        return MathShortcut(handled=False)

    values = numeric_values(last_result)
    selected = select_value_for_arithmetic(values, text)
    if selected is None:
        return MathShortcut(handled=True, text=MATH_NOT_ENOUGH_CONTEXT_MESSAGE if not values else MATH_AMBIGUOUS_VALUE_MESSAGE)

    metric, left = selected
    right = 2.0 if "пополам" in normalize_search_text(text) else parse_number(text)
    if right is None:
        return MathShortcut(handled=True, text="Укажите число для расчета.")
    if operation_type == "divide" and right == 0:
        return MathShortcut(handled=True, text="На ноль делить нельзя.")

    if operation_type == "divide":
        value = left / right
    elif operation_type == "multiply":
        value = left * right
    elif operation_type == "add":
        value = left + right
    else:
        value = left - right

    operation = {
        "type": operation_type,
        "left": {"source": "last_result", "metric": metric},
        "right": {"source": "literal", "value": right},
    }
    return build_result(operation, value, text)


def resolve_percent_deviation_shortcut(text: str, last_result: dict[str, Any] | None) -> MathShortcut:
    if not detect_percent_deviation(text):
        return MathShortcut(handled=False)

    values = numeric_values(last_result)
    plan = values.get("plan")
    fact = values.get("fact")
    deviation = values.get("deviation")
    if plan in {None, 0}:
        return MathShortcut(handled=True, text=PERCENT_DEVIATION_NOT_ENOUGH_DATA_MESSAGE)
    if fact is not None:
        value = (fact - plan) / plan * 100
    elif deviation is not None:
        value = deviation / plan * 100
    else:
        return MathShortcut(handled=True, text=PERCENT_DEVIATION_NOT_ENOUGH_DATA_MESSAGE)

    normalized_value = normalize_value(value)
    operation = {
        "type": "percent",
        "left": {"source": "last_result", "metric": "deviation" if deviation is not None else "fact"},
        "right": {"source": "last_result", "metric": "plan"},
    }
    return MathShortcut(
        handled=True,
        text=f"Отклонение: {format_number(normalized_value)}%",
        result=CalculationResult(
            kind="operation_result",
            rows=[{"value": normalized_value}],
            row_count=1,
            metrics=["value"],
            columns=["value"],
            operation=operation,
        ),
    )


def resolve_math_shortcut(text: str | None, last_result: dict[str, Any] | None) -> MathShortcut:
    if not text:
        return MathShortcut(handled=False)

    percent_result = resolve_percent_deviation_shortcut(text, last_result)
    if percent_result.handled:
        return percent_result
    return resolve_arithmetic_shortcut(text, last_result)
