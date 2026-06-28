import re
from typing import Any


SENSITIVE_COLUMNS = {
    "phone",
    "email",
    "contact",
    "contacts",
    "passport",
    "passport_number",
    "document",
    "document_number",
    "doc_number",
    "fio",
    "person",
    "contract_number",
    "agreement_number",
    "sensitive_kind",
    "is_sensitive",
}
INTERNAL_COLUMNS = {"source_rows", "source_file", "source_sheet", "source_row", "source_col"}
PHONE_RE = re.compile(r"(?<!\d)\+?\d(?:[\s().-]*\d){9,15}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
DOCUMENT_NUMBER_RE = re.compile(r"(?i)(№\s*)[A-Za-zА-Яа-я0-9/_-]{2,}")
FIO_INITIALS_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.){1,2}")
FIO_FULL_RE = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:вич|вна|ич|на|оглы|кызы)\b")


def is_sensitive_column(column: str) -> bool:
    normalized = column.lower()
    return normalized in SENSITIVE_COLUMNS or any(part in normalized for part in SENSITIVE_COLUMNS)


def is_hidden_column(column: str) -> bool:
    return column in INTERNAL_COLUMNS or is_sensitive_column(column)


def phone_match_is_financial_number(match: re.Match[str]) -> bool:
    value = match.group(0)
    start, end = match.span()
    previous_char = match.string[start - 1 : start] if start > 0 else ""
    next_char = match.string[end : end + 1]
    return "." in value or "," in value or previous_char in {".", ","} or next_char in {".", ","}


def replace_phone_match(match: re.Match[str]) -> str:
    if phone_match_is_financial_number(match):
        return match.group(0)
    return "[контакт скрыт]"


def text_has_phone(value: str) -> bool:
    return any(not phone_match_is_financial_number(match) for match in PHONE_RE.finditer(value))


def sanitize_text(value: str) -> str:
    value = FIO_FULL_RE.sub("[скрыто]", value)
    value = FIO_INITIALS_RE.sub("[скрыто]", value)
    value = EMAIL_RE.sub("[контакт скрыт]", value)
    value = PHONE_RE.sub(replace_phone_match, value)
    return DOCUMENT_NUMBER_RE.sub(r"\1[номер документа скрыт]", value)


def detect_sensitive_kind(value: str) -> str | None:
    normalized = value.lower()
    if EMAIL_RE.search(value) or text_has_phone(value):
        return "contact"
    if DOCUMENT_NUMBER_RE.search(value):
        return "document_number"
    if any(marker in normalized for marker in ("паспорт", "номер документа", "№ документа", "серия документа")):
        return "document_number"
    if any(marker in normalized for marker in ("телефон", "email", "e-mail", "почта", "контакт")):
        return "contact"
    if FIO_FULL_RE.search(value) or FIO_INITIALS_RE.search(value):
        return "person"
    return None


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, dict):
        return sanitize_row(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    return value


def is_sensitive_row(row: dict[str, Any]) -> bool:
    return bool(row.get("is_sensitive"))


def sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value if key == "agent" else sanitize_value(value)
        for key, value in row.items()
        if not is_hidden_column(key)
    }


def visible_columns(columns: list[str]) -> list[str]:
    return [column for column in columns if not is_hidden_column(column)]


def visible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sanitize_row(row) for row in rows if not is_sensitive_row(row)]
