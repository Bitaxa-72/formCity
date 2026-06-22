import json
from typing import Any

from app.query_frame import QueryFrame


SENSITIVE_KEYS = {
    "token",
    "key",
    "secret",
    "password",
    "authorization",
    "proxy",
    "phone",
    "email",
    "passport",
}


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(sensitive in normalized for sensitive in SENSITIVE_KEYS)


def redact_value(key: str, value: Any) -> Any:
    if is_sensitive_key(key):
        return "***"
    if isinstance(value, dict):
        return {item_key: redact_value(item_key, item_value) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_value(key, item) for item in value]
    return value


def build_query_frame_log(query_frame: QueryFrame | None) -> dict[str, Any]:
    if query_frame is None:
        return {}

    return {
        "intent": query_frame.intent,
        "report_type": query_frame.report_type,
        "project": query_frame.project,
        "period": query_frame.period.model_dump(by_alias=True),
        "metrics": query_frame.metrics,
        "filter_names": list(query_frame.filters),
        "group_by": query_frame.group_by,
        "ready": query_frame.ready,
        "missing_fields": query_frame.missing_fields,
        "has_operation": query_frame.operation is not None,
    }


def build_request_log_context(
    request_id: str,
    username: str | None,
    update_id: int | None,
    chat_id: int | None,
    query_frame: QueryFrame | None,
    statuses: dict[str, Any],
    errors: dict[str, Any],
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "username": username,
        "update_id": update_id,
        "chat_id": chat_id,
        "intent": query_frame.intent if query_frame else None,
        "query_frame": build_query_frame_log(query_frame),
        "statuses": redact_value("statuses", statuses),
        "errors": redact_value("errors", errors),
    }


def dump_log_context(context: dict[str, Any]) -> str:
    return json.dumps(redact_value("context", context), ensure_ascii=False, sort_keys=True)
