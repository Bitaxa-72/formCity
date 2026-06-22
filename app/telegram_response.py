from pydantic import BaseModel

from app.llm_answer import AnswerDraft
from app.telegram_client import TelegramClient


TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CHUNK_SIZE = 3900
EMPTY_ANSWER_MESSAGE = "Не удалось подготовить ответ."


class TelegramResponseStatus(BaseModel):
    sent: bool
    chunks: int
    error: str | None = None


def split_telegram_text(text: str, chunk_size: int = TELEGRAM_CHUNK_SIZE) -> list[str]:
    prepared = text.strip()
    if not prepared:
        return [EMPTY_ANSWER_MESSAGE]
    if len(prepared) <= chunk_size:
        return [prepared]

    chunks = []
    current = ""
    for line in prepared.splitlines():
        if len(line) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(line[index : index + chunk_size] for index in range(0, len(line), chunk_size))
            continue

        candidate = line if not current else current + "\n" + line
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            current = line

    if current:
        chunks.append(current)

    return chunks


async def send_answer_to_telegram(
    telegram_client: TelegramClient,
    chat_id: int,
    answer_draft: AnswerDraft | None,
) -> TelegramResponseStatus:
    text = answer_draft.text if answer_draft else EMPTY_ANSWER_MESSAGE
    chunks = split_telegram_text(text)

    try:
        for chunk in chunks:
            await telegram_client.send_message(chat_id, chunk)
    except Exception as error:
        return TelegramResponseStatus(sent=False, chunks=0, error=type(error).__name__)

    return TelegramResponseStatus(sent=True, chunks=len(chunks))
