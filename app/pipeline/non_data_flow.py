import asyncio
import logging
from time import perf_counter

from fastapi.encoders import jsonable_encoder

from app.bot.sending import safe_send_message, stop_background_task
from app.bot.telegram_client import TelegramClient
from app.bot.telegram_response import send_answer_to_telegram
from app.db.repositories import UserSessionRepository
from app.llm.answer import (
    LLMAnswerError,
    OpenAILLMAnswerer,
    build_capabilities_answer,
    build_general_fallback_answer,
    build_roadmap_unclear_answer,
)
from app.llm.parser import LLMParsedResponse
from app.pipeline.admin_debug import send_admin_debug
from app.pipeline.query_frame import NON_DATA_QUERY_MESSAGE
from app.pipeline.session_state import preserve_admin_debug_flag
from app.pipeline.text_intents import is_capabilities_question, is_unclear_roadmap_question, is_vague_followup_question
from app.pipeline.timing import record_timing


logger = logging.getLogger("formcity.webhook")


async def handle_general_question(
    parsed_response: LLMParsedResponse,
    *,
    text: str | None,
    chat_id: int,
    update_id: int,
    message_id: int,
    username: str | None,
    request_id: str,
    user_id: int,
    current_state: dict[str, object],
    timings: dict[str, int],
    request_started_at: float,
    typing_task: asyncio.Task[None] | None,
    admin_debug_enabled: bool,
    telegram_client: TelegramClient,
    user_session_repository: UserSessionRepository,
    llm_answerer: OpenAILLMAnswerer,
) -> dict[str, object]:
    answer_error = None
    stage_started_at = perf_counter()
    if is_capabilities_question(text):
        answer_draft = build_capabilities_answer()
        record_timing(timings, "llm_answer", stage_started_at)
    elif is_unclear_roadmap_question(text):
        answer_draft = build_roadmap_unclear_answer()
        record_timing(timings, "llm_answer", stage_started_at)
    elif is_vague_followup_question(text):
        answer_draft = build_general_fallback_answer()
        record_timing(timings, "llm_answer", stage_started_at)
    else:
        try:
            answer_draft = await llm_answerer.build_general_answer(text)
        except LLMAnswerError as error:
            record_timing(timings, "llm_answer", stage_started_at)
            answer_error = str(error)
            answer_draft = build_general_fallback_answer()
            logger.warning(
                "llm_general_answer_failed request_id=%s update_id=%s chat_id=%s username=%s error=%s",
                request_id,
                update_id,
                chat_id,
                username,
                answer_error,
            )
        else:
            record_timing(timings, "llm_answer", stage_started_at)
    await send_admin_debug(
        telegram_client,
        chat_id,
        request_id,
        admin_debug_enabled,
        "03 GeneralAnswerDraft",
        answer_draft,
    )
    await stop_background_task(typing_task)
    stage_started_at = perf_counter()
    telegram_response_status = await send_answer_to_telegram(
        telegram_client,
        chat_id,
        answer_draft,
    )
    record_timing(timings, "telegram_send", stage_started_at)
    await send_admin_debug(
        telegram_client,
        chat_id,
        request_id,
        admin_debug_enabled,
        "04 TelegramResponseStatus",
        telegram_response_status,
    )

    trace = {
        "request_id": request_id,
        "intent": parsed_response.intent,
        "general_answer_done": True,
        "telegram_response_sent": telegram_response_status.sent,
        "timings": timings,
    }
    state_to_save = preserve_admin_debug_flag(current_state, dict(current_state))
    state_to_save["last_trace"] = jsonable_encoder(trace)
    user_session_repository.save_dialog_state(user_id, jsonable_encoder(state_to_save))

    assistant_message_saved = False
    if telegram_response_status.sent:
        user_session_repository.add_assistant_message(
            user_id,
            request_id,
            update_id,
            answer_draft.text,
        )
        assistant_message_saved = True

    record_timing(timings, "total", request_started_at)
    return {
        "ok": True,
        "request_id": request_id,
        "update_id": update_id,
        "message_id": message_id,
        "username": username,
        "access": "allowed",
        "session": "loaded",
        "llm_input": "built",
        "llm_parse": "done",
        "intent": parsed_response.intent,
        "llm_answer": "done",
        "telegram_response_sent": telegram_response_status.sent,
        "telegram_response_chunks": telegram_response_status.chunks,
        "telegram_response_error": telegram_response_status.error,
        "state_saved": True,
        "assistant_message_saved": assistant_message_saved,
        "timings": timings,
    }


async def handle_unsupported_query(
    parsed_response: LLMParsedResponse,
    *,
    chat_id: int,
    update_id: int,
    message_id: int,
    username: str | None,
    request_id: str,
    user_id: int,
    current_state: dict[str, object],
    timings: dict[str, int],
    request_started_at: float,
    typing_task: asyncio.Task[None] | None,
    admin_debug_enabled: bool,
    telegram_client: TelegramClient,
    user_session_repository: UserSessionRepository,
) -> dict[str, object]:
    await stop_background_task(typing_task)
    stage_started_at = perf_counter()
    telegram_response_sent = await safe_send_message(
        telegram_client,
        chat_id,
        NON_DATA_QUERY_MESSAGE,
        request_id,
    )
    record_timing(timings, "telegram_send", stage_started_at)
    record_timing(timings, "total", request_started_at)

    state_to_save = preserve_admin_debug_flag(current_state, dict(current_state))
    state_to_save["last_trace"] = jsonable_encoder(
        {
            "request_id": request_id,
            "intent": parsed_response.intent,
            "non_data_query": True,
            "telegram_response_sent": telegram_response_sent,
            "timings": timings,
        },
    )
    user_session_repository.save_dialog_state(user_id, jsonable_encoder(state_to_save))
    await send_admin_debug(
        telegram_client,
        chat_id,
        request_id,
        admin_debug_enabled,
        "03 UnsupportedResponse",
        {"text": NON_DATA_QUERY_MESSAGE, "sent": telegram_response_sent},
    )
    return {
        "ok": True,
        "request_id": request_id,
        "update_id": update_id,
        "message_id": message_id,
        "username": username,
        "access": "allowed",
        "session": "loaded",
        "llm_input": "built",
        "llm_parse": "done",
        "intent": parsed_response.intent,
        "telegram_response_sent": telegram_response_sent,
        "state_saved": True,
        "timings": timings,
    }
