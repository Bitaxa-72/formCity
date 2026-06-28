from dataclasses import dataclass
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.access import UNAUTHORIZED_ACCESS_MESSAGE
from app.bot.commands import (
    ADMIN_DISABLED_MESSAGE,
    ADMIN_ENABLED_MESSAGE,
    ADMIN_ONLY_MESSAGE,
    BOT_COMMANDS,
    CLEAR_MESSAGE,
    INFO_MESSAGE,
    START_MESSAGE,
)
from app.core.config import Settings
from app.health import PROXY_ERROR_MESSAGE, HealthResult
from app.llm.answer import CAPABILITIES_TEXT, GENERAL_FALLBACK_TEXT, ROADMAP_UNCLEAR_TEXT, LLMAnswerError
from app.llm.parser import LLMParsedResponse, LLMParserError
from app.main import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    CONTEXT_BLOCKED_MESSAGE,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    LLM_PARSE_ERROR_MESSAGE,
    PENDING_CANCEL_MESSAGE,
    PENDING_SHOW_AVAILABLE_ARTICLES,
    PENDING_UNCLEAR_MESSAGE,
    apply_article_clarification_selection,
    apply_dimension_clarification_selection,
    apply_dimension_query_fallback,
    app,
    get_calculation_engine,
    get_domain_resolver,
    get_llm_answerer,
    get_health_checker,
    get_llm_parser,
    get_settings,
    get_telegram_client,
    get_user_session_repository,
)
from app.bot.telegram_client import CHAT_ACTION_TYPING, CHAT_ACTION_UPLOAD_DOCUMENT
from app.pipeline.metric_resolver import REPORT_NOT_CONNECTED_MESSAGE
from app.pipeline.guarded_requests import DATA_MUTATION_BLOCK_MESSAGE, OUT_OF_SCOPE_BLOCK_MESSAGE
from app.pipeline.query_frame import DIMENSION_CLARIFICATION, NON_DATA_QUERY_MESSAGE
from app.pipeline.report_compatibility import (
    PAYMENT_CALENDAR_GROUP_BY_COMPATIBILITY_MESSAGE_TEMPLATE,
    build_payment_calendar_compatibility_message,
)


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.documents: list[dict[str, object]] = []
        self.chat_actions: list[tuple[int, str]] = []
        self.commands: list[dict[str, str]] = []
        self.raise_on_send = False

    async def send_message(self, chat_id: int, text: str) -> None:
        if self.raise_on_send:
            raise RuntimeError("Telegram send failed")
        self.messages.append((chat_id, text))

    async def send_document(self, chat_id: int, file_bytes: bytes, filename: str, caption: str | None = None) -> None:
        if self.raise_on_send:
            raise RuntimeError("Telegram send failed")
        self.documents.append(
            {
                "chat_id": chat_id,
                "file_bytes": file_bytes,
                "filename": filename,
                "caption": caption,
            },
        )

    async def send_chat_action(self, chat_id: int, action: str) -> None:
        if self.raise_on_send:
            raise RuntimeError("Telegram chat action failed")
        self.chat_actions.append((chat_id, action))

    async def set_my_commands(self, commands: list[dict[str, str]]) -> dict[str, object]:
        self.commands = commands
        return {"ok": True}


class FakeHealthChecker:
    def __init__(self) -> None:
        self.result = HealthResult(True)

    async def check_all(self) -> HealthResult:
        return self.result


@dataclass(frozen=True)
class FakeUserSession:
    user: SimpleNamespace
    state: dict[str, object]
    history: list[object]
    last_result: dict[str, object] | None


class FakeUserSessionRepository:
    def __init__(self) -> None:
        self.state: dict[str, object] = {}
        self.last_result: dict[str, object] | None = None
        self.loaded: list[tuple[str, int]] = []
        self.messages: list[dict[str, object]] = []
        self.cleared_user_ids: list[int] = []
        self.saved_states: list[dict[str, object]] = []
        self.saved_last_results: list[dict[str, object]] = []
        self.assistant_messages: list[dict[str, object]] = []

    def load_or_create(self, username: str, chat_id: int) -> FakeUserSession:
        self.loaded.append((username, chat_id))
        return FakeUserSession(user=SimpleNamespace(id=1), state=dict(self.state), history=[], last_result=self.last_result)

    def add_user_message(
        self,
        user_id: int,
        request_id: str,
        update_id: int,
        telegram_message_id: int,
        text: str | None,
    ) -> None:
        self.messages.append(
            {
                "user_id": user_id,
                "request_id": request_id,
                "update_id": update_id,
                "telegram_message_id": telegram_message_id,
                "text": text,
            },
        )

    def clear_state(self, user_id: int) -> None:
        self.cleared_user_ids.append(user_id)
        self.state = {}
        self.last_result = None

    def add_assistant_message(
        self,
        user_id: int,
        request_id: str,
        update_id: int,
        text: str | None,
    ) -> None:
        self.assistant_messages.append(
            {
                "user_id": user_id,
                "request_id": request_id,
                "update_id": update_id,
                "text": text,
            },
        )

    def save_dialog_state(self, user_id: int, data: dict[str, object]) -> None:
        self.state = dict(data)
        self.saved_states.append(
            {
                "user_id": user_id,
                "data": data,
            },
        )

    def save_last_result(
        self,
        user_id: int,
        data: dict[str, object],
        query_frame: dict[str, object],
    ) -> None:
        self.saved_last_results.append(
            {
                "user_id": user_id,
                "data": data,
                "query_frame": query_frame,
            },
        )


class FakeLLMParser:
    def __init__(self) -> None:
        self.inputs: list[object] = []
        self.response = LLMParsedResponse(
            intent="data_query",
            state_delta={"report_type": "payment_calendar", "metrics": ["fact"]},
            confidence=0.9,
        )
        self.error: LLMParserError | None = None

    async def parse(self, llm_input: object) -> LLMParsedResponse:
        self.inputs.append(llm_input)
        if self.error:
            raise self.error
        return self.response


class FakeCalculationEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.result = SimpleNamespace(
            kind="sql_result",
            rows=[{"fact": 100}],
            row_count=1,
            metrics=["fact"],
            columns=["fact"],
            operation=None,
        )

    def calculate(
        self,
        query_frame: object,
        sql_query: object,
        last_result: dict[str, object] | None,
    ) -> SimpleNamespace:
        self.calls.append(
            {
                "query_frame": query_frame,
                "sql_query": sql_query,
                "last_result": last_result,
            },
        )
        return self.result


class FakeDomainResolver:
    def __init__(self) -> None:
        self.calls: list[object] = []
        self.valid = True
        self.errors: list[str] = []
        self.clarification_question: str | None = None
        self.details: dict[str, object] = {}
        self.available_articles = ["ФОТ + налоги (ФОТ)", "Реклама"]

    def resolve(self, query_frame: object) -> SimpleNamespace:
        self.calls.append(query_frame)
        return SimpleNamespace(
            valid=self.valid,
            frame=query_frame,
            errors=self.errors,
            clarification_question=self.clarification_question,
            details=self.details,
        )

    def load_payment_calendar_articles_for_period(
        self,
        project: str | None,
        period: dict[str, str | None],
    ) -> list[str]:
        self.calls.append({"project": project, "period": period})
        return self.available_articles


class FakeLLMAnswerer:
    def __init__(self) -> None:
        self.calls: list[object] = []
        self.general_calls: list[str | None] = []
        self.error: LLMAnswerError | None = None
        self.result = SimpleNamespace(
            text="Факт: 100 руб.",
            used_metrics=["fact"],
            source={},
            warnings=[],
        )

    async def build_general_answer(self, user_message: str | None) -> SimpleNamespace:
        self.general_calls.append(user_message)
        if self.error:
            raise self.error
        return SimpleNamespace(
            text="Здравствуйте. Могу помочь с отчетами и данными проекта.",
            used_metrics=[],
            source={},
            warnings=[],
        )

    async def build_answer(self, response_data: object) -> SimpleNamespace:
        self.calls.append(response_data)
        if self.error:
            raise self.error
        return self.result


client = TestClient(app)
fake_telegram_client = FakeTelegramClient()
fake_health_checker = FakeHealthChecker()
fake_user_session_repository = FakeUserSessionRepository()
fake_llm_parser = FakeLLMParser()
fake_domain_resolver = FakeDomainResolver()
fake_calculation_engine = FakeCalculationEngine()
fake_llm_answerer = FakeLLMAnswerer()


def setup_function() -> None:
    fake_telegram_client.messages.clear()
    fake_telegram_client.documents.clear()
    fake_telegram_client.chat_actions.clear()
    fake_telegram_client.commands.clear()
    fake_telegram_client.raise_on_send = False
    fake_health_checker.result = HealthResult(True)
    fake_llm_parser.inputs.clear()
    fake_llm_parser.error = None
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "payment_calendar", "metrics": ["fact"]},
        confidence=0.9,
    )
    fake_domain_resolver.calls.clear()
    fake_domain_resolver.valid = True
    fake_domain_resolver.errors = []
    fake_domain_resolver.clarification_question = None
    fake_domain_resolver.available_articles = ["ФОТ + налоги (ФОТ)", "Реклама"]
    fake_calculation_engine.calls.clear()
    fake_llm_answerer.error = None
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"fact": 100}],
        row_count=1,
        metrics=["fact"],
        columns=["fact"],
        operation=None,
    )
    fake_llm_answerer.calls.clear()
    fake_llm_answerer.general_calls.clear()
    fake_user_session_repository.loaded.clear()
    fake_user_session_repository.state = {}
    fake_user_session_repository.last_result = None
    fake_user_session_repository.messages.clear()
    fake_user_session_repository.cleared_user_ids.clear()
    fake_user_session_repository.saved_states.clear()
    fake_user_session_repository.saved_last_results.clear()
    fake_user_session_repository.assistant_messages.clear()
    app.dependency_overrides[get_settings] = lambda: Settings(
        bot_token="test-token",
        openai_key="test-openai-key",
        openai_model="test-model",
        proxy="socks5://test-proxy",
        allowed_usernames={"tester", "vitalyfrontend"},
        admin_usernames={"vitalyfrontend"},
    )
    app.dependency_overrides[get_telegram_client] = lambda: fake_telegram_client
    app.dependency_overrides[get_health_checker] = lambda: fake_health_checker
    app.dependency_overrides[get_user_session_repository] = lambda: fake_user_session_repository
    app.dependency_overrides[get_llm_parser] = lambda: fake_llm_parser
    app.dependency_overrides[get_llm_answerer] = lambda: fake_llm_answerer
    app.dependency_overrides[get_domain_resolver] = lambda: fake_domain_resolver
    app.dependency_overrides[get_calculation_engine] = lambda: fake_calculation_engine


def test_health_ok() -> None:
    # Проверяем, что приложение отвечает на простой health check.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_telegram_webhook_message_ok() -> None:
    # Проверяем основной сценарий: Telegram прислал обычное сообщение.
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1001,
            "message": {
                "message_id": 55,
                "date": 1710000000,
                "chat": {"id": 777, "type": "private"},
                "from": {
                    "id": 123,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Привет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["update_id"] == 1001
    assert body["message_id"] == 55
    assert body["username"] == "tester"
    assert body["access"] == "allowed"
    assert body["session"] == "loaded"
    assert body["llm_input"] == "built"
    assert body["llm_parse"] == "done"
    assert body["context"] == "resolved"
    assert body["query_frame"] == "built"
    assert body["query_ready"] is True
    assert body["missing_fields"] == []
    assert body["metrics_valid"] is True
    assert body["metric_errors"] == []
    assert body["sql_compiled"] is True
    assert body["sql_error"] is None
    assert body["calculation_done"] is True
    assert body["calculation_error"] is None
    assert body["result_verified"] is True
    assert body["result_errors"] == []
    assert body["response_data_ready"] is True
    assert body["response_data_errors"] == []
    assert body["llm_answer"] == "done"
    assert body["llm_answer_error"] is None
    assert body["telegram_response_sent"] is True
    assert body["telegram_response_chunks"] == 1
    assert body["telegram_response_error"] is None
    assert body["state_saved"] is True
    assert body["last_result_saved"] is True
    assert body["assistant_message_saved"] is True
    assert body["intent"] == "data_query"
    assert body["request_id"]
    assert fake_telegram_client.messages == [(777, "Факт: 100 руб.")]
    assert fake_telegram_client.chat_actions == [(777, CHAT_ACTION_TYPING)]
    assert fake_user_session_repository.loaded == [("tester", 777)]
    assert fake_user_session_repository.messages[0]["text"] == "Привет"
    assert len(fake_llm_parser.inputs) == 1
    assert len(fake_calculation_engine.calls) == 1
    assert len(fake_llm_answerer.calls) == 1
    assert len(fake_user_session_repository.saved_states) == 1
    assert fake_user_session_repository.saved_states[0]["data"]["metrics"] == ["fact"]
    assert fake_user_session_repository.saved_states[0]["data"]["last_trace"]["telegram_response_sent"] is True
    assert len(fake_user_session_repository.saved_last_results) == 1
    assert fake_user_session_repository.saved_last_results[0]["data"]["rows"] == [{"fact": 100}]
    assert fake_user_session_repository.assistant_messages[0]["text"] == "Факт: 100 руб."


def test_telegram_webhook_handles_math_shortcut_without_llm() -> None:
    fake_user_session_repository.last_result = {
        "kind": "sql_result",
        "rows": [{"article": "ФОТ + налоги (ФОТ)", "plan": 6170978}],
        "row_count": 1,
        "metrics": ["plan"],
        "columns": ["article", "plan"],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1028,
            "message": {
                "message_id": 81,
                "date": 1710000000,
                "chat": {"id": 912, "type": "private"},
                "from": {
                    "id": 148,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "подели на 2",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["math_shortcut"] == "handled"
    assert body["telegram_response_sent"] is True
    assert body["last_result_saved"] is True
    assert fake_telegram_client.messages == [(912, "Результат: 3 085 489 руб.")]
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls == []
    assert fake_user_session_repository.saved_last_results[0]["data"]["rows"] == [{"value": 3085489.0}]


def test_telegram_webhook_math_shortcut_saves_and_uses_metric_clarification() -> None:
    fake_user_session_repository.last_result = {
        "kind": "sql_result",
        "rows": [{"model_revenue": 100, "model_npv": 50}],
        "row_count": 1,
        "metrics": ["model_revenue", "model_npv"],
        "columns": ["model_revenue", "model_npv"],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1030,
            "message": {
                "message_id": 83,
                "date": 1710000000,
                "chat": {"id": 914, "type": "private"},
                "from": {
                    "id": 150,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "подели на 2",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["math_shortcut"] == "handled"
    assert body["last_result_saved"] is False
    assert fake_user_session_repository.state["pending_math_shortcut"] == {"type": "divide", "right": 2.0}
    assert "выручка или NPV" in fake_telegram_client.messages[0][1]

    fake_telegram_client.messages.clear()
    fake_user_session_repository.saved_last_results.clear()
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1031,
            "message": {
                "message_id": 84,
                "date": 1710000001,
                "chat": {"id": 914, "type": "private"},
                "from": {
                    "id": 150,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "выручка",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["math_shortcut"] == "handled"
    assert body["last_result_saved"] is True
    assert "pending_math_shortcut" not in fake_user_session_repository.state
    assert fake_telegram_client.messages == [(914, "Результат: 50 руб.")]
    assert fake_user_session_repository.saved_last_results[0]["data"]["rows"] == [{"value": 50.0}]


def test_telegram_webhook_handles_percent_deviation_shortcut_missing_data() -> None:
    fake_user_session_repository.last_result = {
        "kind": "sql_result",
        "rows": [{"article": "ФОТ + налоги (ФОТ)", "plan": 6170978}],
        "row_count": 1,
        "metrics": ["plan"],
        "columns": ["article", "plan"],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1029,
            "message": {
                "message_id": 82,
                "date": 1710000000,
                "chat": {"id": 913, "type": "private"},
                "from": {
                    "id": 149,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какое отклонение в процентах?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["math_shortcut"] == "handled"
    assert body["telegram_response_sent"] is True
    assert body["last_result_saved"] is False
    assert fake_telegram_client.messages == [
        (913, "Для расчета отклонения в процентах нужны план и факт. Сейчас в контексте не хватает данных."),
    ]
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls == []


def test_telegram_webhook_sends_fallback_when_llm_answer_fails() -> None:
    fake_llm_answerer.error = LLMAnswerError("LLM returned invalid answer schema")
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"plan": 2900000, "fact": None, "deviation": None, "source_rows": 1}],
        row_count=1,
        metrics=["fact"],
        columns=["plan", "fact", "deviation", "source_rows"],
        operation=None,
    )
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "metrics": ["fact"],
            "filters": {"article": "Реклама"},
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1002,
            "message": {
                "message_id": 56,
                "date": 1710000000,
                "chat": {"id": 777, "type": "private"},
                "from": {
                    "id": 123,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Платежный календарь факт по рекламе за май",
            },
        },
    )

    body = response.json()

    expected_text = (
        'По статье "Реклама" за май 2026 факт не заполнен.\n'
        "План: 2 900 000 руб.\n"
        "Факт: нет данных\n"
        "Отклонение: нет данных"
    )
    assert response.status_code == 200
    assert body["llm_answer"] == "done"
    assert body["llm_answer_error"] == "LLM returned invalid answer schema"
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(777, expected_text)]
    assert fake_user_session_repository.assistant_messages[0]["text"] == expected_text


def test_telegram_webhook_general_question_uses_llm_without_context_pipeline() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="general_question",
        state_delta={},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1003,
            "message": {
                "message_id": 57,
                "date": 1710000000,
                "chat": {"id": 778, "type": "private"},
                "from": {
                    "id": 124,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "привет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "general_question"
    assert body["llm_answer"] == "done"
    assert body["telegram_response_sent"] is True
    assert fake_llm_answerer.general_calls == ["привет"]
    assert fake_llm_answerer.calls == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_telegram_client.messages == [(778, "Здравствуйте. Могу помочь с отчетами и данными проекта.")]
    assert fake_user_session_repository.assistant_messages[0]["text"] == "Здравствуйте. Могу помочь с отчетами и данными проекта."


def test_telegram_webhook_guarded_out_of_scope_request_does_not_reuse_context() -> None:
    fake_user_session_repository.state = {
        "last_intent": "dimension_query",
        "report_type": "stock_for_sale",
        "dimension": "floor",
        "project": "obvodny",
    }
    fake_user_session_repository.last_result = {
        "report_type": "stock_for_sale",
        "rows": [{"floor_number": 1}],
        "metrics": [],
    }
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "stock_for_sale", "dimension": "floor_number"},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1056,
            "message": {
                "message_id": 109,
                "date": 1710000000,
                "chat": {"id": 939, "type": "private"},
                "from": {
                    "id": 175,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какая погода?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert fake_telegram_client.messages == [(939, OUT_OF_SCOPE_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_user_session_repository.state["report_type"] is None
    assert fake_user_session_repository.last_result is None
    assert fake_user_session_repository.cleared_user_ids == [1]


def test_telegram_webhook_guarded_keyboard_garbage_does_not_reuse_context() -> None:
    fake_user_session_repository.state = {
        "last_intent": "dimension_query",
        "report_type": "stock_for_sale",
        "dimension": "floor",
        "project": "obvodny",
    }
    fake_user_session_repository.last_result = {
        "report_type": "stock_for_sale",
        "rows": [{"floor_number": 1}],
        "metrics": [],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1058,
            "message": {
                "message_id": 111,
                "date": 1710000000,
                "chat": {"id": 941, "type": "private"},
                "from": {
                    "id": 177,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "lf",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert fake_telegram_client.messages == [(941, OUT_OF_SCOPE_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_user_session_repository.last_result is None


def test_telegram_webhook_guarded_project_delivery_question_does_not_reuse_context() -> None:
    fake_user_session_repository.state = {
        "last_intent": "dimension_query",
        "report_type": "stock_for_sale",
        "dimension": "floor",
        "project": "obvodny",
    }
    fake_user_session_repository.last_result = {
        "report_type": "stock_for_sale",
        "rows": [{"floor_number": 1}],
        "metrics": [],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1059,
            "message": {
                "message_id": 112,
                "date": 1710000000,
                "chat": {"id": 942, "type": "private"},
                "from": {
                    "id": 178,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "когда сдача проекта?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert fake_telegram_client.messages == [(942, OUT_OF_SCOPE_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_user_session_repository.last_result is None


def test_telegram_webhook_guarded_mutation_request_does_not_reuse_context() -> None:
    fake_user_session_repository.state = {
        "last_intent": "dimension_query",
        "report_type": "stock_for_sale",
        "dimension": "floor",
        "project": "obvodny",
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1057,
            "message": {
                "message_id": 110,
                "date": 1710000000,
                "chat": {"id": 940, "type": "private"},
                "from": {
                    "id": 176,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "измени данные в таблице",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert fake_telegram_client.messages == [(940, DATA_MUTATION_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_user_session_repository.state["report_type"] is None


def test_telegram_webhook_capabilities_question_uses_backend_answer() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="general_question",
        state_delta={},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1028,
            "message": {
                "message_id": 81,
                "date": 1710000000,
                "chat": {"id": 912, "type": "private"},
                "from": {
                    "id": 148,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Что ты умеешь?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "general_question"
    assert body["llm_answer"] == "done"
    assert fake_llm_parser.inputs
    assert fake_llm_answerer.general_calls == []
    assert fake_llm_answerer.calls == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_telegram_client.messages == [(912, CAPABILITIES_TEXT)]
    assert fake_user_session_repository.assistant_messages[0]["text"] == CAPABILITIES_TEXT


def test_telegram_webhook_capabilities_question_handles_unsupported_intent() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="unsupported",
        state_delta={},
        confidence=0.7,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1054,
            "message": {
                "message_id": 107,
                "date": 1710000000,
                "chat": {"id": 938, "type": "private"},
                "from": {
                    "id": 174,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какие отчеты доступны?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "unsupported"
    assert fake_llm_answerer.general_calls == []
    assert fake_domain_resolver.calls == []
    assert fake_telegram_client.messages == [(938, CAPABILITIES_TEXT)]


def test_telegram_webhook_unclear_roadmap_general_question_uses_backend_answer() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="general_question",
        state_delta={},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1048,
            "message": {
                "message_id": 101,
                "date": 1710000000,
                "chat": {"id": 932, "type": "private"},
                "from": {
                    "id": 168,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "дорожная карта какая-то фигня",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "general_question"
    assert body["llm_answer"] == "done"
    assert fake_llm_answerer.general_calls == []
    assert fake_llm_answerer.calls == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_telegram_client.messages == [(932, ROADMAP_UNCLEAR_TEXT)]
    assert fake_user_session_repository.assistant_messages[0]["text"] == ROADMAP_UNCLEAR_TEXT


def test_telegram_webhook_vague_followup_uses_backend_fallback() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="general_question",
        state_delta={},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1030,
            "message": {
                "message_id": 83,
                "date": 1710000000,
                "chat": {"id": 914, "type": "private"},
                "from": {
                    "id": 150,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "ну и?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "general_question"
    assert body["llm_answer"] == "done"
    assert fake_llm_parser.inputs
    assert fake_llm_answerer.general_calls == []
    assert fake_telegram_client.messages == [(914, GENERAL_FALLBACK_TEXT)]
    assert fake_user_session_repository.assistant_messages[0]["text"] == GENERAL_FALLBACK_TEXT


def test_telegram_webhook_general_question_uses_fallback_when_answer_fails() -> None:
    fake_llm_answerer.error = LLMAnswerError("LLM returned invalid general answer schema")
    fake_llm_parser.response = LLMParsedResponse(
        intent="general_question",
        state_delta={},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1004,
            "message": {
                "message_id": 58,
                "date": 1710000000,
                "chat": {"id": 779, "type": "private"},
                "from": {
                    "id": 125,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "привет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "general_question"
    assert body["llm_answer"] == "done"
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(779, GENERAL_FALLBACK_TEXT)]


def test_telegram_webhook_unsupported_does_not_reuse_previous_data_context() -> None:
    fake_user_session_repository.state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
        "metrics": ["plan"],
        "filters": {"article": "ФОТ + налоги (ФОТ)"},
    }
    fake_llm_parser.response = LLMParsedResponse(
        intent="unsupported",
        state_delta={},
        confidence=0.7,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1005,
            "message": {
                "message_id": 59,
                "date": 1710000000,
                "chat": {"id": 780, "type": "private"},
                "from": {
                    "id": 126,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Сколько этажей",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(780, OUT_OF_SCOPE_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert fake_llm_answerer.calls == []
    assert fake_user_session_repository.state["report_type"] is None
    assert fake_user_session_repository.state["last_trace"]["guarded_non_data_request"] is True


def test_dependency_health_ok() -> None:
    # Проверяем status endpoint для внешних зависимостей.
    response = client.get("/health/dependencies")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "failed_service": None}


def test_setup_telegram_commands() -> None:
    response = client.post("/telegram/commands")

    body = response.json()

    assert response.status_code == 200
    assert body == {"ok": True, "commands": BOT_COMMANDS}
    assert fake_telegram_client.commands == BOT_COMMANDS


def test_telegram_webhook_denies_unknown_username() -> None:
    # Проверяем отказ пользователю вне whitelist.
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1003,
            "message": {
                "message_id": 56,
                "date": 1710000000,
                "chat": {"id": 888, "type": "private"},
                "from": {
                    "id": 124,
                    "is_bot": False,
                    "first_name": "Unknown",
                    "username": "unknown",
                },
                "text": "Привет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["access"] == "denied"
    assert body["request_id"]
    assert fake_telegram_client.messages == [
        (888, UNAUTHORIZED_ACCESS_MESSAGE),
    ]
    assert fake_telegram_client.chat_actions == []
    assert fake_user_session_repository.loaded == []


def test_telegram_webhook_denies_missing_username() -> None:
    # Проверяем, что без username доступа нет.
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1004,
            "message": {
                "message_id": 57,
                "date": 1710000000,
                "chat": {"id": 889, "type": "private"},
                "from": {
                    "id": 125,
                    "is_bot": False,
                    "first_name": "NoUsername",
                },
                "text": "Привет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["access"] == "denied"
    assert fake_telegram_client.messages == [
        (889, UNAUTHORIZED_ACCESS_MESSAGE),
    ]


def test_telegram_webhook_does_not_fail_when_send_message_fails() -> None:
    # Проверяем, что ошибка отправки в Telegram не ломает webhook.
    fake_telegram_client.raise_on_send = True

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1011,
            "message": {
                "message_id": 64,
                "date": 1710000000,
                "chat": {"id": 896, "type": "private"},
                "from": {
                    "id": 132,
                    "is_bot": False,
                    "first_name": "Unknown",
                    "username": "unknown",
                },
                "text": "Привет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["access"] == "denied"


def test_telegram_webhook_start_command() -> None:
    # Проверяем быстрый ответ на /start для пользователя из whitelist.
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1005,
            "message": {
                "message_id": 58,
                "date": 1710000000,
                "chat": {"id": 890, "type": "private"},
                "from": {
                    "id": 126,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "/start",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["command"] == "/start"
    assert fake_telegram_client.messages == [(890, START_MESSAGE)]
    assert fake_user_session_repository.loaded == [("tester", 890)]
    assert fake_user_session_repository.cleared_user_ids == [1]
    assert fake_llm_parser.inputs == []


def test_telegram_webhook_start_preserves_admin_debug() -> None:
    fake_user_session_repository.state = {
        "admin_debug_enabled": True,
        "report_type": "payment_calendar",
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1019,
            "message": {
                "message_id": 72,
                "date": 1710000000,
                "chat": {"id": 903, "type": "private"},
                "from": {
                    "id": 139,
                    "is_bot": False,
                    "first_name": "Vitaly",
                    "username": "vitalyfrontend",
                },
                "text": "/start",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["command"] == "/start"
    assert fake_user_session_repository.cleared_user_ids == [1]
    assert fake_user_session_repository.state == {"admin_debug_enabled": True}


def test_telegram_webhook_admin_denies_non_admin() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1015,
            "message": {
                "message_id": 68,
                "date": 1710000000,
                "chat": {"id": 900, "type": "private"},
                "from": {
                    "id": 136,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "/admin",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["admin"] == "denied"
    assert fake_telegram_client.messages == [(900, ADMIN_ONLY_MESSAGE)]
    assert fake_user_session_repository.saved_states == []


def test_telegram_webhook_admin_toggles_debug() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1016,
            "message": {
                "message_id": 69,
                "date": 1710000000,
                "chat": {"id": 901, "type": "private"},
                "from": {
                    "id": 137,
                    "is_bot": False,
                    "first_name": "Vitaly",
                    "username": "vitalyfrontend",
                },
                "text": "/admin",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["admin_debug_enabled"] is True
    assert fake_telegram_client.messages == [(901, ADMIN_ENABLED_MESSAGE)]
    assert fake_user_session_repository.state["admin_debug_enabled"] is True

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1017,
            "message": {
                "message_id": 70,
                "date": 1710000000,
                "chat": {"id": 901, "type": "private"},
                "from": {
                    "id": 137,
                    "is_bot": False,
                    "first_name": "Vitaly",
                    "username": "vitalyfrontend",
                },
                "text": "/admin",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["admin_debug_enabled"] is False
    assert fake_telegram_client.messages[-1] == (901, ADMIN_DISABLED_MESSAGE)
    assert fake_user_session_repository.state["admin_debug_enabled"] is False


def test_telegram_webhook_admin_debug_sends_stage_json() -> None:
    fake_user_session_repository.state = {"admin_debug_enabled": True}

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1018,
            "message": {
                "message_id": 71,
                "date": 1710000000,
                "chat": {"id": 902, "type": "private"},
                "from": {
                    "id": 138,
                    "is_bot": False,
                    "first_name": "Vitaly",
                    "username": "vitalyfrontend",
                },
                "text": "Факт",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    debug_messages = [text for _, text in fake_telegram_client.messages if text.startswith("ADMIN DEBUG:")]
    assert any("01 LLMInput" in message for message in debug_messages)
    assert any("04 QueryFrame" in message for message in debug_messages)
    assert any("12 TelegramResponseStatus" in message for message in debug_messages)
    assert fake_telegram_client.messages[-2][1] == fake_llm_answerer.result.text
    assert fake_user_session_repository.state["admin_debug_enabled"] is True


def test_telegram_webhook_handles_llm_parse_error() -> None:
    # Проверяем fallback, если LLM вернула невалидный JSON/schema.
    fake_llm_parser.error = LLMParserError("invalid schema")

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1012,
            "message": {
                "message_id": 65,
                "date": 1710000000,
                "chat": {"id": 897, "type": "private"},
                "from": {
                    "id": 133,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Дай выручку",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["llm_parse"] == "failed"
    assert fake_telegram_client.messages == [(897, LLM_PARSE_ERROR_MESSAGE)]


def test_telegram_webhook_sends_query_frame_clarification_when_not_ready() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "payment_calendar"},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1021,
            "message": {
                "message_id": 74,
                "date": 1710000000,
                "chat": {"id": 905, "type": "private"},
                "from": {
                    "id": 141,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Платежный календарь",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["query_ready"] is False
    assert body["missing_fields"] == ["metrics"]
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(905, "Уточните метрику для запроса.")]
    assert fake_calculation_engine.calls == []
    assert fake_user_session_repository.saved_states[0]["data"]["awaiting_clarification"] is True


def test_telegram_webhook_report_type_clarification_reuses_partial_query() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "metrics": ["fact"],
            "period": {"label": "май"},
            "filters": {"article": "Реклама"},
        },
        confidence=0.9,
    )

    first_response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1101,
            "message": {
                "message_id": 154,
                "date": 1710000000,
                "chat": {"id": 985, "type": "private"},
                "from": {
                    "id": 221,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "факт по рекламе за май",
            },
        },
    )

    first_body = first_response.json()
    saved_state = fake_user_session_repository.state

    assert first_response.status_code == 200
    assert first_body["query_ready"] is False
    assert first_body["missing_fields"] == ["report_type"]
    assert saved_state["awaiting_clarification"] is True
    assert saved_state["clarification_kind"] == "report_type"
    assert saved_state["clarification_base_state"]["metrics"] == ["fact"]
    assert saved_state["clarification_base_state"]["filters"] == {"article": "Реклама"}

    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "payment_calendar"},
        confidence=0.9,
    )

    second_response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1102,
            "message": {
                "message_id": 155,
                "date": 1710000001,
                "chat": {"id": 985, "type": "private"},
                "from": {
                    "id": 221,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "платежный календарь",
            },
        },
    )

    second_body = second_response.json()
    query_frame = fake_calculation_engine.calls[-1]["query_frame"]

    assert second_response.status_code == 200
    assert second_body["query_ready"] is True
    assert query_frame.report_type == "payment_calendar"
    assert query_frame.metrics == ["fact"]
    assert query_frame.filters == {"article": "Реклама"}


def test_telegram_webhook_rejects_payment_calendar_sales_metric_before_domain_resolution() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["fact"],
            "filters": {"article": "выручка"},
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1031,
            "message": {
                "message_id": 84,
                "date": 1710000000,
                "chat": {"id": 915, "type": "private"},
                "from": {
                    "id": 151,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "платежный календарь московский выручка за май",
            },
        },
    )

    body = response.json()
    expected_text = build_payment_calendar_compatibility_message("выручка")

    assert response.status_code == 200
    assert body["compatibility_valid"] is False
    assert body["compatibility_error"] == "metric_not_supported_for_payment_calendar"
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(915, expected_text)]
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    assert "report_type" not in fake_user_session_repository.saved_states[0]["data"]


def test_telegram_webhook_rejects_payment_calendar_sales_metric_before_metric_clarification() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1032,
            "message": {
                "message_id": 85,
                "date": 1710000000,
                "chat": {"id": 916, "type": "private"},
                "from": {
                    "id": 152,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "платежный календарь московский цена метра за май",
            },
        },
    )

    body = response.json()
    expected_text = build_payment_calendar_compatibility_message("цена метра")

    assert response.status_code == 200
    assert body["compatibility_valid"] is False
    assert body["compatibility_error"] == "metric_not_supported_for_payment_calendar"
    assert body["missing_fields"] == []
    assert fake_telegram_client.messages == [(916, expected_text)]
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []


def test_telegram_webhook_rejects_payment_calendar_foreign_group_by() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["plan"],
            "group_by": ["floor"],
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1041,
            "message": {
                "message_id": 94,
                "date": 1710000000,
                "chat": {"id": 925, "type": "private"},
                "from": {
                    "id": 161,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "платежный календарь московский план по этажам за май",
            },
        },
    )

    body = response.json()
    expected_text = PAYMENT_CALENDAR_GROUP_BY_COMPATIBILITY_MESSAGE_TEMPLATE.format(group_by="этажам")

    assert response.status_code == 200
    assert body["compatibility_valid"] is False
    assert body["compatibility_error"] == "group_by_not_supported_for_payment_calendar"
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(925, expected_text)]
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []
    saved_state = fake_user_session_repository.saved_states[0]["data"]
    assert saved_state[CONTEXT_BLOCKED_AFTER_ERROR] is True
    assert saved_state[FAILED_QUERY_ERROR] == "group_by_not_supported_for_payment_calendar"
    assert saved_state[FAILED_QUERY_STATE]["group_by"] == ["floor"]


def test_telegram_webhook_blocks_short_followup_after_compatibility_error() -> None:
    fake_user_session_repository.state = {
        CONTEXT_BLOCKED_AFTER_ERROR: True,
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["fact"],
        "filters": {"article": "Реклама"},
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1042,
            "message": {
                "message_id": 95,
                "date": 1710000000,
                "chat": {"id": 926, "type": "private"},
                "from": {
                    "id": 162,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "по проектам",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["context_blocked_after_error"] is True
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(926, CONTEXT_BLOCKED_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls == []
    assert fake_calculation_engine.calls == []


def test_telegram_webhook_corrects_failed_group_by_after_compatibility_error() -> None:
    fake_user_session_repository.state = {
        CONTEXT_BLOCKED_AFTER_ERROR: True,
        FAILED_QUERY_ERROR: "group_by_not_supported_for_payment_calendar",
        FAILED_QUERY_STATE: {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
            "metrics": ["plan"],
            "filters": {},
            "group_by": ["floor"],
            "last_intent": "data_query",
            "awaiting_clarification": False,
        },
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["fact"],
        "filters": {"article": "Реклама"},
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1044,
            "message": {
                "message_id": 97,
                "date": 1710000000,
                "chat": {"id": 928, "type": "private"},
                "from": {
                    "id": 164,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "по проетам",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].group_by == ["project"]
    assert fake_domain_resolver.calls[0].project == "all"
    assert fake_calculation_engine.calls[0]["query_frame"].group_by == ["project"]
    assert fake_calculation_engine.calls[0]["query_frame"].project == "all"
    assert fake_user_session_repository.state["group_by"] == ["project"]
    assert fake_user_session_repository.state["project"] == "all"
    assert fake_user_session_repository.state["metrics"] == ["plan"]
    assert CONTEXT_BLOCKED_AFTER_ERROR not in fake_user_session_repository.state
    assert FAILED_QUERY_ERROR not in fake_user_session_repository.state
    assert FAILED_QUERY_STATE not in fake_user_session_repository.state


def test_telegram_webhook_corrects_failed_payment_calendar_metric_after_compatibility_error() -> None:
    fake_user_session_repository.state = {
        CONTEXT_BLOCKED_AFTER_ERROR: True,
        FAILED_QUERY_ERROR: "metric_not_supported_for_payment_calendar",
        FAILED_QUERY_STATE: {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
            "metrics": ["plan", "fact", "deviation"],
            "filters": {"article": "Выручка"},
            "group_by": [],
            "last_intent": "data_query",
            "awaiting_clarification": False,
        },
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["fact"],
        "filters": {"article": "Реклама"},
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1045,
            "message": {
                "message_id": 98,
                "date": 1710000000,
                "chat": {"id": 929, "type": "private"},
                "from": {
                    "id": 165,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "факт",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].metrics == ["fact"]
    assert fake_domain_resolver.calls[0].filters == {}
    assert fake_calculation_engine.calls[0]["query_frame"].metrics == ["fact"]
    assert fake_user_session_repository.state["metrics"] == ["fact"]
    assert fake_user_session_repository.state["filters"] == {}
    assert CONTEXT_BLOCKED_AFTER_ERROR not in fake_user_session_repository.state
    assert FAILED_QUERY_ERROR not in fake_user_session_repository.state
    assert FAILED_QUERY_STATE not in fake_user_session_repository.state


def test_telegram_webhook_corrects_failed_payment_calendar_metric_to_summary_view() -> None:
    fake_user_session_repository.state = {
        CONTEXT_BLOCKED_AFTER_ERROR: True,
        FAILED_QUERY_ERROR: "metric_not_supported_for_payment_calendar",
        FAILED_QUERY_STATE: {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
            "metrics": ["plan", "fact", "deviation"],
            "filters": {"article": "Выручка"},
            "group_by": [],
            "last_intent": "data_query",
            "awaiting_clarification": False,
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1046,
            "message": {
                "message_id": 99,
                "date": 1710000000,
                "chat": {"id": 930, "type": "private"},
                "from": {
                    "id": 166,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "итоги",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].view == "summary"
    assert fake_domain_resolver.calls[0].filters == {
        "article_kind": ["balance_start", "income_total", "payment_total", "balance_end"],
    }
    assert fake_user_session_repository.state["view"] == "summary"


def test_telegram_webhook_corrects_failed_roadmap_metric_to_steps_view() -> None:
    fake_user_session_repository.state = {
        CONTEXT_BLOCKED_AFTER_ERROR: True,
        FAILED_QUERY_ERROR: "metric_not_supported_for_roadmap",
        FAILED_QUERY_STATE: {
            "report_type": "roadmap",
            "project": "all",
            "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель 2026"},
            "metrics": ["fact"],
            "filters": {},
            "group_by": [],
            "last_intent": "data_query",
            "awaiting_clarification": False,
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1047,
            "message": {
                "message_id": 100,
                "date": 1710000000,
                "chat": {"id": 931, "type": "private"},
                "from": {
                    "id": 167,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "этапы",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].report_type == "roadmap"
    assert fake_domain_resolver.calls[0].view == "roadmap_steps"
    assert fake_domain_resolver.calls[0].metrics == ["duration_min", "duration_max"]
    assert fake_domain_resolver.calls[0].period.label == "апрель 2026"
    assert fake_user_session_repository.state["view"] == "roadmap_steps"
    assert fake_user_session_repository.state["metrics"] == ["duration_min", "duration_max"]
    assert CONTEXT_BLOCKED_AFTER_ERROR not in fake_user_session_repository.state
    assert FAILED_QUERY_ERROR not in fake_user_session_repository.state
    assert FAILED_QUERY_STATE not in fake_user_session_repository.state


def test_telegram_webhook_treats_model_summary_alias_as_new_model_query() -> None:
    fake_user_session_repository.last_result = {
        "kind": "sql_result",
        "rows": [
            {
                "model_revenue": 11166655390.46,
                "model_cost_of_sales": -6900517274,
                "model_gross_profit": 4266138116.46,
                "model_net_profit": 1287811999.18,
                "model_npv": -346372619.92,
            },
        ],
        "row_count": 1,
        "metrics": [
            "model_revenue",
            "model_cost_of_sales",
            "model_gross_profit",
            "model_net_profit",
            "model_npv",
        ],
        "columns": [
            "model_revenue",
            "model_cost_of_sales",
            "model_gross_profit",
            "model_net_profit",
            "model_npv",
        ],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1048,
            "message": {
                "message_id": 101,
                "date": 1710000000,
                "chat": {"id": 932, "type": "private"},
                "from": {
                    "id": 168,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "краткая сводка модели",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].report_type == "model"
    assert fake_domain_resolver.calls[0].view == "model_summary"
    assert fake_domain_resolver.calls[0].metrics == [
        "model_revenue",
        "model_cost_of_sales",
        "model_gross_profit",
        "model_net_profit",
        "model_npv",
    ]
    assert fake_user_session_repository.state["report_type"] == "model"
    assert fake_user_session_repository.state["view"] == "model_summary"


def test_telegram_webhook_treats_model_period_without_metric_as_new_summary_query() -> None:
    fake_user_session_repository.state = {
        "report_type": "model",
        "project": "obvodny",
        "period": {"label": "февраль"},
        "metrics": ["model_npv"],
        "view": "model_kpi",
        "filters": {"scenario": "current"},
        "group_by": [],
        "last_intent": "data_query",
        "awaiting_clarification": False,
    }
    fake_user_session_repository.last_result = {
        "kind": "sql_result",
        "rows": [{"model_npv": -335889498.39}],
        "row_count": 1,
        "metrics": ["model_npv"],
        "columns": ["model_npv"],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1050,
            "message": {
                "message_id": 103,
                "date": 1710000000,
                "chat": {"id": 934, "type": "private"},
                "from": {
                    "id": 170,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "модель март",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].report_type == "model"
    assert fake_domain_resolver.calls[0].view == "model_summary"
    assert fake_domain_resolver.calls[0].period.label == "март"
    assert fake_domain_resolver.calls[0].metrics == [
        "model_revenue",
        "model_cost_of_sales",
        "model_gross_profit",
        "model_net_profit",
        "model_npv",
    ]
    assert fake_user_session_repository.state["view"] == "model_summary"
    assert fake_user_session_repository.state["period"]["label"] == "март"
    assert fake_user_session_repository.state["metrics"] == [
        "model_revenue",
        "model_cost_of_sales",
        "model_gross_profit",
        "model_net_profit",
        "model_npv",
    ]


def test_telegram_webhook_treats_model_snapshot_alias_as_new_dimension_query() -> None:
    fake_user_session_repository.last_result = {
        "kind": "sql_result",
        "rows": [{"model_revenue": 11166655390.46, "model_npv": -346372619.92}],
        "row_count": 1,
        "metrics": ["model_revenue", "model_npv"],
        "columns": ["model_revenue", "model_npv"],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1049,
            "message": {
                "message_id": 102,
                "date": 1710000000,
                "chat": {"id": 933, "type": "private"},
                "from": {
                    "id": 169,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какие срезы модели есть?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].report_type == "model"
    assert fake_domain_resolver.calls[0].intent == "dimension_query"
    assert fake_domain_resolver.calls[0].view == "model_available_snapshots"
    assert fake_domain_resolver.calls[0].dimension == "snapshot_month"
    assert fake_domain_resolver.calls[0].metrics == []
    assert fake_user_session_repository.state["report_type"] == "model"
    assert fake_user_session_repository.state["view"] == "model_available_snapshots"
    assert fake_user_session_repository.state["dimension"] == "snapshot_month"


def test_telegram_webhook_blocks_model_sensitive_request_without_llm() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1051,
            "message": {
                "message_id": 104,
                "date": 1710000000,
                "chat": {"id": 935, "type": "private"},
                "from": {
                    "id": 171,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "модель покажи контакты",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls == []
    assert fake_domain_resolver.calls == []
    assert fake_telegram_client.messages
    assert "по правилам безопасности" in fake_telegram_client.messages[0][1]


def test_telegram_webhook_model_available_metrics_context_does_not_send_pdf() -> None:
    fake_user_session_repository.state = {
        "report_type": "model",
        "project": "obvodny",
        "metrics": ["model_npv"],
        "view": "model_kpi",
        "filters": {"scenario": "current"},
        "group_by": [],
        "last_intent": "data_query",
        "awaiting_clarification": False,
    }
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"metric": f"Показатель {index}"} for index in range(40)],
        row_count=40,
        metrics=[],
        columns=["metric"],
        operation=None,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1052,
            "message": {
                "message_id": 105,
                "date": 1710000000,
                "chat": {"id": 936, "type": "private"},
                "from": {
                    "id": 172,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какие показатели есть?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_telegram_client.documents == []
    assert fake_telegram_client.messages
    assert fake_domain_resolver.calls[0].report_type == "model"
    assert fake_domain_resolver.calls[0].view == "model_available_metrics"


def test_telegram_webhook_model_raw_sheet_list_without_llm() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 10520,
            "message": {
                "message_id": 1050,
                "date": 1710000000,
                "chat": {"id": 9360, "type": "private"},
                "from": {
                    "id": 1720,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какие листы есть в модели?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].report_type == "model"
    assert fake_domain_resolver.calls[0].intent == "dimension_query"
    assert fake_domain_resolver.calls[0].view == "model_raw_sheets"
    assert fake_domain_resolver.calls[0].dimension == "raw_sheet"


def test_telegram_webhook_model_raw_rows_without_llm() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 10521,
            "message": {
                "message_id": 1051,
                "date": 1710000000,
                "chat": {"id": 9361, "type": "private"},
                "from": {
                    "id": 1721,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "модель финмодель апрель",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_domain_resolver.calls[0].report_type == "model"
    assert fake_domain_resolver.calls[0].view == "model_raw_rows"
    assert fake_domain_resolver.calls[0].filters == {"raw_sheet": "financial_model"}
    assert fake_domain_resolver.calls[0].period.label == "апрель"


def test_telegram_webhook_model_short_metric_context_replaces_metric_without_llm() -> None:
    fake_user_session_repository.state = {
        "report_type": "model",
        "project": "obvodny",
        "period": {"label": "апрель"},
        "metrics": ["model_npv"],
        "view": "model_kpi",
        "filters": {"scenario": "current"},
        "group_by": [],
        "last_intent": "data_query",
        "awaiting_clarification": False,
    }
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"model_roe": 45.46}],
        row_count=1,
        metrics=["model_roe"],
        columns=["model_roe"],
        operation=None,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1053,
            "message": {
                "message_id": 106,
                "date": 1710000000,
                "chat": {"id": 937, "type": "private"},
                "from": {
                    "id": 173,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "ROE",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls[0]["query_frame"].metrics == ["model_roe"]


def test_telegram_webhook_model_short_metric_context_keeps_period() -> None:
    fake_user_session_repository.state = {
        "report_type": "model",
        "project": "obvodny",
        "period": {"label": "февраль"},
        "metrics": ["model_revenue"],
        "view": "model_kpi",
        "filters": {"scenario": "current"},
        "group_by": [],
        "last_intent": "data_query",
        "awaiting_clarification": False,
    }
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"model_npv": -335889498.39}],
        row_count=1,
        metrics=["model_npv"],
        columns=["model_npv"],
        operation=None,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1055,
            "message": {
                "message_id": 108,
                "date": 1710000000,
                "chat": {"id": 939, "type": "private"},
                "from": {
                    "id": 175,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "а NPV?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_llm_parser.inputs == []
    query_frame = fake_calculation_engine.calls[0]["query_frame"]
    assert query_frame.metrics == ["model_npv"]
    assert query_frame.period.label == "февраль"


def test_telegram_webhook_model_unknown_metric_does_not_return_summary() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1054,
            "message": {
                "message_id": 107,
                "date": 1710000000,
                "chat": {"id": 938, "type": "private"},
                "from": {
                    "id": 174,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "модель космический показатель апрель",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert fake_calculation_engine.calls == []
    assert fake_telegram_client.messages
    assert "Не нашел такой показатель в модели" in fake_telegram_client.messages[0][1]


def test_telegram_webhook_rejects_floor_question_misread_as_roadmap() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "roadmap",
            "project": "all",
            "period": {"label": "апрель"},
            "metrics": ["duration_min", "duration_max"],
            "view": "full_roadmap",
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1049,
            "message": {
                "message_id": 102,
                "date": 1710000000,
                "chat": {"id": 933, "type": "private"},
                "from": {
                    "id": 169,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "сколько этажей?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert fake_telegram_client.messages == [(933, OUT_OF_SCOPE_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls == []


def test_telegram_webhook_allows_full_query_after_compatibility_error() -> None:
    fake_user_session_repository.state = {
        CONTEXT_BLOCKED_AFTER_ERROR: True,
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["fact"],
        "filters": {"article": "Реклама"},
    }
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["plan"],
            "filters": {"article": "ФОТ"},
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1043,
            "message": {
                "message_id": 96,
                "date": 1710000000,
                "chat": {"id": 927, "type": "private"},
                "from": {
                    "id": 163,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "платежный календарь московский план по ФОТ за май",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["llm_parse"] == "done"
    assert body["telegram_response_sent"] is True
    assert len(fake_llm_parser.inputs) == 1
    assert CONTEXT_BLOCKED_AFTER_ERROR not in fake_user_session_repository.state


def test_telegram_webhook_routes_sales_plan_execution_report() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "sales_plan_execution", "period": {"label": "may"}},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1026,
            "message": {
                "message_id": 79,
                "date": 1710000000,
                "chat": {"id": 914, "type": "private"},
                "from": {
                    "id": 150,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "sales plan execution may",
            },
        },
    )

    body = response.json()
    saved_state = fake_user_session_repository.saved_states[0]["data"]

    assert response.status_code == 200
    assert body["query_ready"] is True
    assert body["missing_fields"] == []
    assert body["metrics_valid"] is True
    assert body["metric_errors"] == []
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages
    assert fake_telegram_client.messages[0][0] == 914
    assert fake_domain_resolver.calls[0].report_type == "sales_plan_execution"
    assert fake_calculation_engine.calls[0]["query_frame"].report_type == "sales_plan_execution"
    assert saved_state["report_type"] == "sales_plan_execution"
    assert saved_state["awaiting_clarification"] is False


def test_telegram_webhook_sends_domain_clarification() -> None:
    fake_domain_resolver.valid = False
    fake_domain_resolver.errors = ["article_ambiguous"]
    fake_domain_resolver.clarification_question = "Уточните статью."
    fake_domain_resolver.details = {
        "clarification_kind": "article",
        "article_candidates": ["ФОТ + налоги (ФОТ)", "Реклама"],
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1013,
            "message": {
                "message_id": 66,
                "date": 1710000000,
                "chat": {"id": 898, "type": "private"},
                "from": {
                    "id": 134,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Факт по аренде",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["domain_valid"] is False
    assert body["domain_errors"] == ["article_ambiguous"]
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(898, "Уточните статью.")]
    assert fake_calculation_engine.calls == []
    saved_state = fake_user_session_repository.saved_states[0]["data"]
    assert saved_state["awaiting_clarification"] is True
    assert saved_state["clarification_kind"] == "article"
    assert saved_state["clarification_options"] == ["ФОТ + налоги (ФОТ)", "Реклама"]


def test_apply_article_clarification_selection_uses_saved_options() -> None:
    parsed = LLMParsedResponse(
        intent="data_query",
        state_delta={"metrics": ["plan"], "filters": {"article": "фот + налоги"}},
        confidence=0.9,
    )

    updated = apply_article_clarification_selection(
        {
            "awaiting_clarification": True,
            "clarification_kind": "article",
            "clarification_options": ["ФОТ + налоги (ФОТ)", "Реклама"],
        },
        parsed,
        "фот + налоги",
    )

    assert updated.state_delta.filters == {"article": "ФОТ + налоги (ФОТ)"}


def test_apply_dimension_query_fallback_detects_expense_article_list() -> None:
    parsed = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "payment_calendar"},
        confidence=0.9,
    )

    updated = apply_dimension_query_fallback(
        parsed,
        "какие статьи расходов есть в платежном календаре?",
    )

    assert updated.intent == "dimension_query"
    assert updated.state_delta.report_type == "payment_calendar"
    assert updated.state_delta.dimension == "article"
    assert updated.state_delta.filters == {"article_kind": "detail"}


def test_apply_dimension_clarification_selection_detects_expense_article_list() -> None:
    parsed = LLMParsedResponse(
        intent="data_query",
        state_delta={"metrics": ["fact"]},
        confidence=0.9,
    )

    updated = apply_dimension_clarification_selection(
        {
            "awaiting_clarification": True,
            "clarification_kind": "dimension",
        },
        parsed,
        "статьи расходов",
    )

    assert updated.intent == "dimension_query"
    assert updated.state_delta.dimension == "article"
    assert updated.state_delta.metrics is None
    assert updated.state_delta.filters == {"article_kind": "detail"}


def test_telegram_webhook_fallback_handles_expense_article_list_query() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="dimension_query",
        state_delta={"report_type": "payment_calendar"},
        confidence=0.9,
    )
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"article": "Реклама"}, {"article": "ФОТ + налоги (ФОТ)"}],
        row_count=2,
        metrics=[],
        columns=["article"],
        operation=None,
    )
    fake_llm_answerer.error = LLMAnswerError("LLM returned invalid answer schema")

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1026,
            "message": {
                "message_id": 79,
                "date": 1710000000,
                "chat": {"id": 910, "type": "private"},
                "from": {
                    "id": 146,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "какие статьи расходов есть в платежном календаре?",
            },
        },
    )

    body = response.json()
    saved_state = fake_user_session_repository.saved_states[0]["data"]

    assert response.status_code == 200
    assert body["query_ready"] is True
    assert body["missing_fields"] == []
    assert saved_state["last_intent"] == "dimension_query"
    assert saved_state["dimension"] == "article"
    assert saved_state["filters"] == {"article_kind": "detail"}
    assert "Статьи:" in fake_telegram_client.messages[0][1]
    assert "- Реклама" in fake_telegram_client.messages[0][1]


def test_telegram_webhook_sets_dimension_clarification_kind() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="dimension_query",
        state_delta={"report_type": "payment_calendar"},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1037,
            "message": {
                "message_id": 90,
                "date": 1710000000,
                "chat": {"id": 921, "type": "private"},
                "from": {
                    "id": 157,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "платежный календарь какие есть?",
            },
        },
    )

    body = response.json()
    saved_state = fake_user_session_repository.saved_states[0]["data"]

    assert response.status_code == 200
    assert body["query_ready"] is False
    assert body["missing_fields"] == ["dimension"]
    assert saved_state["awaiting_clarification"] is True
    assert saved_state["clarification_kind"] == "dimension"
    assert fake_telegram_client.messages[0][1] == DIMENSION_CLARIFICATION


def test_telegram_webhook_handles_dimension_clarification_answer() -> None:
    fake_user_session_repository.state = {
        "report_type": "payment_calendar",
        "project": "all",
        "period": {"from": None, "to": None, "label": None},
        "metrics": [],
        "filters": {},
        "group_by": [],
        "last_intent": "dimension_query",
        "awaiting_clarification": True,
        "clarification_kind": "dimension",
        "clarification_target": DIMENSION_CLARIFICATION,
        "clarification_base_state": {
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": None, "to": None, "label": None},
            "metrics": [],
            "filters": {},
            "group_by": [],
            "last_intent": "dimension_query",
            "awaiting_clarification": False,
            "clarification_kind": None,
            "clarification_target": None,
        },
    }
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"metrics": ["fact"]},
        confidence=0.9,
    )
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[{"article": "Реклама"}, {"article": "ФОТ + налоги (ФОТ)"}],
        row_count=2,
        metrics=[],
        columns=["article"],
        operation=None,
    )
    fake_llm_answerer.error = LLMAnswerError("LLM returned invalid answer schema")

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1038,
            "message": {
                "message_id": 91,
                "date": 1710000000,
                "chat": {"id": 922, "type": "private"},
                "from": {
                    "id": 158,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "статьи расходов",
            },
        },
    )

    body = response.json()
    saved_state = fake_user_session_repository.saved_states[0]["data"]

    assert response.status_code == 200
    assert body["query_ready"] is True
    assert body["missing_fields"] == []
    assert saved_state["last_intent"] == "dimension_query"
    assert saved_state["dimension"] == "article"
    assert saved_state["filters"] == {"article_kind": "detail"}
    assert saved_state["awaiting_clarification"] is False
    assert "Статьи:" in fake_telegram_client.messages[0][1]


def test_telegram_webhook_does_not_save_missing_article_filter() -> None:
    fake_domain_resolver.valid = False
    fake_domain_resolver.errors = ["article_not_found"]
    fake_domain_resolver.clarification_question = "Не нашел такую статью в платежном календаре."
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": {"label": "май"},
            "metrics": ["fact"],
            "filters": {"article": "реклама"},
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1022,
            "message": {
                "message_id": 75,
                "date": 1710000000,
                "chat": {"id": 906, "type": "private"},
                "from": {
                    "id": 142,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Платежный календарь обводный факт по рекламе за май",
            },
        },
    )

    body = response.json()
    saved_state = fake_user_session_repository.saved_states[0]["data"]

    assert response.status_code == 200
    assert body["domain_valid"] is False
    assert body["domain_errors"] == ["article_not_found"]
    assert body["telegram_response_sent"] is True
    assert saved_state["awaiting_clarification"] is False
    assert saved_state["filters"] == {}
    assert saved_state["report_type"] == "payment_calendar"
    assert saved_state["project"] == "obvodny"
    assert fake_calculation_engine.calls == []


def test_telegram_webhook_does_not_save_missing_period_context() -> None:
    fake_user_session_repository.state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["deviation"],
        "filters": {"article": "ФОТ + налоги (ФОТ)"},
        "group_by": [],
        "last_intent": "data_query",
        "awaiting_clarification": False,
    }
    fake_domain_resolver.valid = False
    fake_domain_resolver.errors = ["period_data_not_found"]
    fake_domain_resolver.clarification_question = (
        "За указанный период нет данных. Доступные периоды: 2026-02, 2026-03, 2026-04, 2026-05."
    )
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "period": {"from": "2026-06-01", "to": "2026-06-30", "label": "июнь 2026"},
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1027,
            "message": {
                "message_id": 80,
                "date": 1710000000,
                "chat": {"id": 911, "type": "private"},
                "from": {
                    "id": 147,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "а за июнь?",
            },
        },
    )

    body = response.json()
    saved_state = fake_user_session_repository.saved_states[0]["data"]

    assert response.status_code == 200
    assert body["domain_valid"] is False
    assert body["domain_errors"] == ["period_data_not_found"]
    assert body["telegram_response_sent"] is True
    assert saved_state["period"] == {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"}
    assert saved_state["project"] == "moskovsky"
    assert saved_state["metrics"] == ["deviation"]
    assert saved_state["filters"] == {"article": "ФОТ + налоги (ФОТ)"}
    assert saved_state["awaiting_clarification"] is False
    assert fake_calculation_engine.calls == []


def test_telegram_webhook_sends_not_allowed_metric_message() -> None:
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"report_type": "roadmap", "metrics": ["fact"]},
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1015,
            "message": {
                "message_id": 68,
                "date": 1710000000,
                "chat": {"id": 900, "type": "private"},
                "from": {
                    "id": 136,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Когда сдача проекта?",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["guarded_non_data_request"] is True
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(900, OUT_OF_SCOPE_BLOCK_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls == []
    assert fake_llm_answerer.calls == []
    assert fake_user_session_repository.saved_states[0]["data"]["last_trace"]["guarded_non_data_request"] is True


def test_telegram_webhook_sends_large_report_as_pdf() -> None:
    fake_calculation_engine.result = SimpleNamespace(
        kind="sql_result",
        rows=[
            {
                "article": f"Article {index}",
                "plan": index * 10,
                "fact": index,
                "deviation": index - index * 10,
            }
            for index in range(31)
        ],
        row_count=31,
        metrics=["plan", "fact", "deviation"],
        columns=["article", "plan", "fact", "deviation"],
        operation=None,
    )
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={
            "report_type": "payment_calendar",
            "metrics": ["plan", "fact", "deviation"],
            "group_by": ["article"],
        },
        confidence=0.9,
    )

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1014,
            "message": {
                "message_id": 67,
                "date": 1710000000,
                "chat": {"id": 899, "type": "private"},
                "from": {
                    "id": 135,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Подробный отчет",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["telegram_response_sent"] is True
    assert body["telegram_response_chunks"] == 2
    assert body["llm_answer"] == "skipped"
    assert fake_telegram_client.messages == [(899, "Отчет слишком большой, оформлю вам PDF.")]
    assert fake_telegram_client.chat_actions == [
        (899, CHAT_ACTION_TYPING),
        (899, CHAT_ACTION_UPLOAD_DOCUMENT),
    ]
    assert len(fake_telegram_client.documents) == 1
    assert fake_telegram_client.documents[0]["filename"] == "payment_calendar.pdf"
    assert fake_telegram_client.documents[0]["file_bytes"]
    assert fake_llm_answerer.calls == []


def test_telegram_webhook_info_command_with_bot_suffix() -> None:
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1006,
            "message": {
                "message_id": 59,
                "date": 1710000000,
                "chat": {"id": 891, "type": "private"},
                "from": {
                    "id": 127,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "/info@formcity_bot",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["command"] == "/info"
    assert fake_telegram_client.messages == [(891, INFO_MESSAGE)]


def test_telegram_webhook_clear_command() -> None:
    # Проверяем быстрый ответ на /clear.
    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1007,
            "message": {
                "message_id": 60,
                "date": 1710000000,
                "chat": {"id": 892, "type": "private"},
                "from": {
                    "id": 128,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "/clear",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["command"] == "/clear"
    assert fake_telegram_client.messages == [(892, CLEAR_MESSAGE)]
    assert fake_telegram_client.chat_actions == []
    assert fake_user_session_repository.cleared_user_ids == [1]


def test_telegram_webhook_clear_preserves_admin_debug() -> None:
    fake_user_session_repository.state = {
        "admin_debug_enabled": True,
        "report_type": "payment_calendar",
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1020,
            "message": {
                "message_id": 73,
                "date": 1710000000,
                "chat": {"id": 904, "type": "private"},
                "from": {
                    "id": 140,
                    "is_bot": False,
                    "first_name": "Vitaly",
                    "username": "vitalyfrontend",
                },
                "text": "/clear",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["command"] == "/clear"
    assert fake_user_session_repository.cleared_user_ids == [1]
    assert fake_user_session_repository.state == {"admin_debug_enabled": True}


def test_telegram_webhook_pending_article_list_confirmation() -> None:
    fake_user_session_repository.state = {
        "pending_action": PENDING_SHOW_AVAILABLE_ARTICLES,
        "pending_payload": {
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель"},
            "missing_article": "реклама",
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1023,
            "message": {
                "message_id": 76,
                "date": 1710000000,
                "chat": {"id": 907, "type": "private"},
                "from": {
                    "id": 143,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "давай",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["pending_action"] == "handled"
    assert body["available_articles"] == 2
    assert "Доступные статьи в платежном календаре по Обводному за апрель 2026:" in fake_telegram_client.messages[0][1]
    assert "- ФОТ + налоги (ФОТ)" in fake_telegram_client.messages[0][1]
    assert fake_llm_parser.inputs == []
    assert fake_calculation_engine.calls == []
    assert "pending_action" not in fake_user_session_repository.state
    assert "pending_payload" not in fake_user_session_repository.state


def test_telegram_webhook_pending_article_list_keyboard_typo_confirmation() -> None:
    fake_user_session_repository.state = {
        "pending_action": PENDING_SHOW_AVAILABLE_ARTICLES,
        "pending_payload": {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "missing_article": "космическая статья 123",
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1039,
            "message": {
                "message_id": 92,
                "date": 1710000000,
                "chat": {"id": 923, "type": "private"},
                "from": {
                    "id": 159,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "lf",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["pending_action"] == "handled"
    assert "Доступные статьи" in fake_telegram_client.messages[0][1]
    assert "pending_action" not in fake_user_session_repository.state


def test_telegram_webhook_pending_article_list_keeps_state_on_unclear_short_text() -> None:
    fake_user_session_repository.state = {
        "pending_action": PENDING_SHOW_AVAILABLE_ARTICLES,
        "pending_payload": {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "missing_article": "космическая статья 123",
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1040,
            "message": {
                "message_id": 93,
                "date": 1710000000,
                "chat": {"id": 924, "type": "private"},
                "from": {
                    "id": 160,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "xx",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["pending_action"] == "unclear"
    assert fake_telegram_client.messages == [(924, PENDING_UNCLEAR_MESSAGE)]
    assert fake_user_session_repository.state["pending_action"] == PENDING_SHOW_AVAILABLE_ARTICLES
    assert fake_llm_parser.inputs == []


def test_telegram_webhook_pending_article_list_cancellation() -> None:
    fake_user_session_repository.state = {
        "pending_action": PENDING_SHOW_AVAILABLE_ARTICLES,
        "pending_payload": {
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель"},
            "missing_article": "реклама",
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1024,
            "message": {
                "message_id": 77,
                "date": 1710000000,
                "chat": {"id": 908, "type": "private"},
                "from": {
                    "id": 144,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "не надо",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["pending_action"] == "cancelled"
    assert fake_telegram_client.messages == [(908, PENDING_CANCEL_MESSAGE)]
    assert fake_llm_parser.inputs == []
    assert "pending_action" not in fake_user_session_repository.state


def test_telegram_webhook_pending_article_list_new_query_goes_to_pipeline() -> None:
    fake_user_session_repository.state = {
        "pending_action": PENDING_SHOW_AVAILABLE_ARTICLES,
        "pending_payload": {
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель"},
            "missing_article": "реклама",
        },
    }

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1025,
            "message": {
                "message_id": 78,
                "date": 1710000000,
                "chat": {"id": 909, "type": "private"},
                "from": {
                    "id": 145,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "давай московский факт по ФОТ",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["llm_parse"] == "done"
    assert fake_telegram_client.messages == [(909, "Факт: 100 руб.")]
    assert len(fake_llm_parser.inputs) == 1
    assert len(fake_calculation_engine.calls) == 1
    assert "pending_action" not in fake_user_session_repository.state


def test_telegram_webhook_does_not_run_dependency_health_for_regular_message() -> None:
    fake_health_checker.result = HealthResult(False, "proxy", PROXY_ERROR_MESSAGE)

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1008,
            "message": {
                "message_id": 61,
                "date": 1710000000,
                "chat": {"id": 893, "type": "private"},
                "from": {
                    "id": 129,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "tester",
                },
                "text": "Дай выручку",
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["llm_parse"] == "done"
    assert body["telegram_response_sent"] is True
    assert fake_telegram_client.messages == [(893, "Факт: 100 руб.")]
    assert len(fake_llm_parser.inputs) == 1


def test_telegram_webhook_invalid_update() -> None:
    # Проверяем валидацию update без обязательного update_id.
    response = client.post("/webhook/telegram", json={"message": {}})

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is False
    assert body["error"] == "invalid_update"
    assert body["request_id"]


def test_telegram_webhook_ignored_update() -> None:
    # Проверяем, что события без message не ломают webhook.
    response = client.post(
        "/webhook/telegram",
        json={"update_id": 1002, "callback_query": {"id": "abc"}},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is True
    assert body["ignored"] is True
    assert body["request_id"]
