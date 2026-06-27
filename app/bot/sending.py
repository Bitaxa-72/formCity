import asyncio
import logging
from contextlib import suppress

from app.bot.telegram_client import TelegramClient


logger = logging.getLogger("formcity.webhook")


async def safe_send_message(
    telegram_client: TelegramClient,
    chat_id: int,
    text: str,
    request_id: str,
) -> bool:
    try:
        await telegram_client.send_message(chat_id, text)
        return True
    except Exception:
        logger.exception(
            "send_message_failed request_id=%s chat_id=%s",
            request_id,
            chat_id,
        )
        return False


async def safe_send_chat_action(
    telegram_client: TelegramClient,
    chat_id: int,
    action: str,
    request_id: str,
) -> bool:
    try:
        await telegram_client.send_chat_action(chat_id, action)
        return True
    except Exception:
        logger.warning(
            "send_chat_action_failed request_id=%s chat_id=%s action=%s",
            request_id,
            chat_id,
            action,
        )
        return False


async def keep_chat_action(
    telegram_client: TelegramClient,
    chat_id: int,
    action: str,
    request_id: str,
    interval_seconds: int = 4,
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await safe_send_chat_action(telegram_client, chat_id, action, request_id)


async def stop_background_task(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
