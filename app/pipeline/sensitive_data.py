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
    "contract_number",
    "agreement_number",
    "sensitive_kind",
    "is_sensitive",
}
INTERNAL_COLUMNS = {"source_rows", "source_file", "source_sheet", "source_row", "source_col"}
PHONE_RE = re.compile(r"(?<!\d)\+?\d(?:[\s().-]*\d){9,15}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
DOCUMENT_NUMBER_RE = re.compile(r"(?i)(№\s*)[A-Za-zА-Яа-я0-9/_-]{2,}")


def is_sensitive_column(column: str) -> bool:
    normalized = column.lower()
    return normalized in SENSITIVE_COLUMNS or any(part in normalized for part in SENSITIVE_COLUMNS)


def is_hidden_column(column: str) -> bool:
    return column in INTERNAL_COLUMNS or is_sensitive_column(column)


def sanitize_text(value: str) -> str:
    value = EMAIL_RE.sub("[contact hidden]", value)
    value = PHONE_RE.sub("[contact hidden]", value)
    return DOCUMENT_NUMBER_RE.sub(r"\1[document hidden]", value)


def detect_sensitive_kind(value: str) -> str | None:
    normalized = value.lower()
    if EMAIL_RE.search(value) or PHONE_RE.search(value):
        return "contact"
    if DOCUMENT_NUMBER_RE.search(value):
        return "document_number"
    if any(marker in normalized for marker in ("паспорт", "номер документа", "№ документа", "серия документа")):
        return "document_number"
    if any(marker in normalized for marker in ("телефон", "email", "e-mail", "почта", "контакт")):
        return "contact"
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
        key: sanitize_value(value)
        for key, value in row.items()
        if not is_hidden_column(key)
    }


def visible_columns(columns: list[str]) -> list[str]:
    return [column for column in columns if not is_hidden_column(column)]


def visible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sanitize_row(row) for row in rows if not is_sensitive_row(row)]
