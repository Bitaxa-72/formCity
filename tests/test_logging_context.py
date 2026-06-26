from app.pipeline.logging_context import build_query_frame_log, build_request_log_context, dump_log_context, redact_value
from app.pipeline.query_frame import build_query_frame


def test_build_query_frame_log_hides_filter_values() -> None:
    query_frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "metrics": ["revenue"],
            "filters": {
                "phone": "phone-value",
                "room_type": "studio",
            },
        },
    )

    log_data = build_query_frame_log(query_frame)

    assert log_data["filter_names"] == ["phone", "room_type"]
    assert "filters" not in log_data


def test_redact_value_masks_sensitive_keys() -> None:
    data = {
        "openai_key": "private-value",
        "nested": {
            "phone": "phone-value",
            "safe": "value",
        },
    }

    redacted = redact_value("root", data)

    assert redacted == {
        "openai_key": "***",
        "nested": {
            "phone": "***",
            "safe": "value",
        },
    }


def test_build_request_log_context_contains_safe_summary() -> None:
    query_frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "obvodny",
            "metrics": ["revenue"],
        },
    )

    context = build_request_log_context(
        request_id="request-id",
        username="tester",
        update_id=1001,
        chat_id=777,
        query_frame=query_frame,
        statuses={"telegram_response_sent": True},
        errors={"sql_error": None},
    )

    assert context["request_id"] == "request-id"
    assert context["username"] == "tester"
    assert context["intent"] == "data_query"
    assert context["query_frame"]["metrics"] == ["revenue"]
    assert context["statuses"] == {"telegram_response_sent": True}


def test_dump_log_context_returns_json_without_ascii_escape() -> None:
    dumped = dump_log_context({"message": "Привет", "token": "private-value"})

    assert '"message": "Привет"' in dumped
    assert '"token": "***"' in dumped
    assert "private-value" not in dumped
