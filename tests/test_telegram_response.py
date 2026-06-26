import pytest

from app.llm.answer import AnswerDraft
from app.bot.telegram_response import EMPTY_ANSWER_MESSAGE, send_answer_to_telegram, split_telegram_text


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.raise_on_send = False

    async def send_message(self, chat_id: int, text: str) -> None:
        if self.raise_on_send:
            raise RuntimeError("send failed")
        self.messages.append((chat_id, text))


def test_split_telegram_text_keeps_short_text() -> None:
    assert split_telegram_text("Ответ") == ["Ответ"]


def test_split_telegram_text_uses_empty_fallback() -> None:
    assert split_telegram_text("   ") == [EMPTY_ANSWER_MESSAGE]


def test_split_telegram_text_splits_long_line() -> None:
    chunks = split_telegram_text("a" * 9, chunk_size=4)

    assert chunks == ["aaaa", "aaaa", "a"]


@pytest.mark.anyio
async def test_send_answer_to_telegram_sends_chunks() -> None:
    telegram_client = FakeTelegramClient()
    answer = AnswerDraft(text="line1\nline2\nline3", used_metrics=[], source={}, warnings=[])

    status = await send_answer_to_telegram(telegram_client, 777, answer)

    assert status.sent is True
    assert status.chunks == 1
    assert status.error is None
    assert telegram_client.messages == [(777, "line1\nline2\nline3")]


@pytest.mark.anyio
async def test_send_answer_to_telegram_handles_send_error() -> None:
    telegram_client = FakeTelegramClient()
    telegram_client.raise_on_send = True
    answer = AnswerDraft(text="Ответ", used_metrics=[], source={}, warnings=[])

    status = await send_answer_to_telegram(telegram_client, 777, answer)

    assert status.sent is False
    assert status.chunks == 0
    assert status.error == "RuntimeError"
