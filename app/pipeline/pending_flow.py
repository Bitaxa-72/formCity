from fastapi.encoders import jsonable_encoder

from app.bot.sending import safe_send_message
from app.bot.telegram_client import TelegramClient
from app.bot.telegram_response import split_telegram_text
from app.db.repositories import UserSessionRepository
from app.pipeline.domain_resolver import DomainResolver
from app.pipeline.pending_actions import (
    PENDING_CANCEL_MESSAGE,
    PENDING_SHOW_AVAILABLE_ARTICLES,
    PENDING_UNCLEAR_MESSAGE,
    build_available_articles_message,
    classify_pending_response,
    clear_pending_action,
)


async def handle_pending_action(
    current_state: dict[str, object],
    *,
    text: str | None,
    chat_id: int,
    user_id: int,
    request_id: str,
    telegram_client: TelegramClient,
    user_session_repository: UserSessionRepository,
    domain_resolver: DomainResolver,
) -> tuple[dict[str, object] | None, dict[str, object]]:
    if current_state.get("pending_action") != PENDING_SHOW_AVAILABLE_ARTICLES:
        return None, current_state

    pending_payload = current_state.get("pending_payload")
    pending_action = classify_pending_response(text)

    if pending_action == "unclear":
        await safe_send_message(telegram_client, chat_id, PENDING_UNCLEAR_MESSAGE, request_id)
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "session": "loaded",
            "pending_action": "unclear",
            "telegram_response_sent": True,
        }, current_state

    state_to_save = clear_pending_action(current_state)
    user_session_repository.save_dialog_state(
        user_id,
        jsonable_encoder(state_to_save),
    )

    if pending_action == "confirm" and isinstance(pending_payload, dict):
        articles = domain_resolver.load_payment_calendar_articles_for_period(
            pending_payload.get("project") if isinstance(pending_payload.get("project"), str) else None,
            pending_payload.get("period") if isinstance(pending_payload.get("period"), dict) else {},
        )
        response_text = build_available_articles_message(articles, pending_payload)
        for chunk in split_telegram_text(response_text):
            await safe_send_message(telegram_client, chat_id, chunk, request_id)
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "session": "loaded",
            "pending_action": "handled",
            "available_articles": len(articles),
            "telegram_response_sent": True,
        }, state_to_save

    if pending_action == "cancel":
        await safe_send_message(telegram_client, chat_id, PENDING_CANCEL_MESSAGE, request_id)
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "session": "loaded",
            "pending_action": "cancelled",
            "telegram_response_sent": True,
        }, state_to_save

    return None, state_to_save
