from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.access import UNAUTHORIZED_ACCESS_MESSAGE
from app.commands import CLEAR_MESSAGE, INFO_MESSAGE, START_MESSAGE
from app.config import Settings
from app.health import LLM_ERROR_MESSAGE, PROXY_ERROR_MESSAGE, TELEGRAM_ERROR_MESSAGE, HealthResult
from app.llm_parser import LLMParsedResponse, LLMParserError
from app.main import (
    LLM_PARSE_ERROR_MESSAGE,
    app,
    get_calculation_engine,
    get_llm_answerer,
    get_health_checker,
    get_llm_parser,
    get_settings,
    get_telegram_client,
    get_user_session_repository,
)


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.raise_on_send = False

    async def send_message(self, chat_id: int, text: str) -> None:
        if self.raise_on_send:
            raise RuntimeError("Telegram send failed")
        self.messages.append((chat_id, text))


class FakeHealthChecker:
    def __init__(self) -> None:
        self.result = HealthResult(True)

    async def check_all(self) -> HealthResult:
        return self.result


class FakeUserSessionRepository:
    def __init__(self) -> None:
        self.loaded: list[tuple[str, int]] = []
        self.messages: list[dict[str, object]] = []
        self.cleared_user_ids: list[int] = []
        self.saved_states: list[dict[str, object]] = []
        self.saved_last_results: list[dict[str, object]] = []
        self.assistant_messages: list[dict[str, object]] = []

    def load_or_create(self, username: str, chat_id: int) -> SimpleNamespace:
        self.loaded.append((username, chat_id))
        return SimpleNamespace(user=SimpleNamespace(id=1), state={}, history=[], last_result=None)

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
            state_delta={"metrics": ["revenue"]},
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
            rows=[{"revenue": 100}],
            row_count=1,
            metrics=["revenue"],
            columns=["revenue"],
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


class FakeLLMAnswerer:
    def __init__(self) -> None:
        self.calls: list[object] = []
        self.result = SimpleNamespace(
            text="Выручка: 100 руб.",
            used_metrics=["revenue"],
            source={},
            warnings=[],
        )

    async def build_answer(self, response_data: object) -> SimpleNamespace:
        self.calls.append(response_data)
        return self.result


client = TestClient(app)
fake_telegram_client = FakeTelegramClient()
fake_health_checker = FakeHealthChecker()
fake_user_session_repository = FakeUserSessionRepository()
fake_llm_parser = FakeLLMParser()
fake_calculation_engine = FakeCalculationEngine()
fake_llm_answerer = FakeLLMAnswerer()


def setup_function() -> None:
    fake_telegram_client.messages.clear()
    fake_telegram_client.raise_on_send = False
    fake_health_checker.result = HealthResult(True)
    fake_llm_parser.inputs.clear()
    fake_llm_parser.error = None
    fake_llm_parser.response = LLMParsedResponse(
        intent="data_query",
        state_delta={"metrics": ["revenue"]},
        confidence=0.9,
    )
    fake_calculation_engine.calls.clear()
    fake_llm_answerer.calls.clear()
    fake_user_session_repository.loaded.clear()
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
        allowed_usernames={"tester"},
    )
    app.dependency_overrides[get_telegram_client] = lambda: fake_telegram_client
    app.dependency_overrides[get_health_checker] = lambda: fake_health_checker
    app.dependency_overrides[get_user_session_repository] = lambda: fake_user_session_repository
    app.dependency_overrides[get_llm_parser] = lambda: fake_llm_parser
    app.dependency_overrides[get_llm_answerer] = lambda: fake_llm_answerer
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
    assert fake_telegram_client.messages == [(777, "Выручка: 100 руб.")]
    assert fake_user_session_repository.loaded == [("tester", 777)]
    assert fake_user_session_repository.messages[0]["text"] == "Привет"
    assert len(fake_llm_parser.inputs) == 1
    assert len(fake_calculation_engine.calls) == 1
    assert len(fake_llm_answerer.calls) == 1
    assert len(fake_user_session_repository.saved_states) == 1
    assert fake_user_session_repository.saved_states[0]["data"]["metrics"] == ["revenue"]
    assert fake_user_session_repository.saved_states[0]["data"]["last_trace"]["telegram_response_sent"] is True
    assert len(fake_user_session_repository.saved_last_results) == 1
    assert fake_user_session_repository.saved_last_results[0]["data"]["rows"] == [{"revenue": 100}]
    assert fake_user_session_repository.assistant_messages[0]["text"] == "Выручка: 100 руб."


def test_dependency_health_ok() -> None:
    # Проверяем status endpoint для внешних зависимостей.
    response = client.get("/health/dependencies")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "failed_service": None}


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
    assert fake_llm_parser.inputs == []


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


def test_telegram_webhook_info_command_with_bot_suffix() -> None:
    # Проверяем команду с suffix бота: /info@bot_name.
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
    assert fake_user_session_repository.cleared_user_ids == [1]


def test_telegram_webhook_stops_when_proxy_fails() -> None:
    # Проверяем, что при падении proxy обычный запрос не идет дальше.
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
    assert body["health"] == "failed"
    assert body["failed_service"] == "proxy"
    assert fake_telegram_client.messages == [(893, PROXY_ERROR_MESSAGE)]
    assert fake_llm_parser.inputs == []


def test_telegram_webhook_stops_when_telegram_fails() -> None:
    # Проверяем ошибку Telegram API.
    fake_health_checker.result = HealthResult(False, "telegram", TELEGRAM_ERROR_MESSAGE)

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1009,
            "message": {
                "message_id": 62,
                "date": 1710000000,
                "chat": {"id": 894, "type": "private"},
                "from": {
                    "id": 130,
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
    assert body["health"] == "failed"
    assert body["failed_service"] == "telegram"
    assert fake_telegram_client.messages == [(894, TELEGRAM_ERROR_MESSAGE)]


def test_telegram_webhook_stops_when_llm_fails() -> None:
    # Проверяем ошибку LLM token/balance.
    fake_health_checker.result = HealthResult(False, "llm", LLM_ERROR_MESSAGE)

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1010,
            "message": {
                "message_id": 63,
                "date": 1710000000,
                "chat": {"id": 895, "type": "private"},
                "from": {
                    "id": 131,
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
    assert body["health"] == "failed"
    assert body["failed_service"] == "llm"
    assert fake_telegram_client.messages == [(895, LLM_ERROR_MESSAGE)]


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
