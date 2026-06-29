import asyncio
import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.bot.commands import normalize_command
from app.bot.sending import keep_chat_action, safe_send_chat_action, safe_send_message, stop_background_task
from app.bot.telegram_client import CHAT_ACTION_TYPING, CHAT_ACTION_UPLOAD_DOCUMENT, TelegramClient
from app.bot.telegram_response import TelegramResponseStatus, send_answer_to_telegram
from app.bot.telegram_schemas import TelegramUpdate
from app.core.access import UNAUTHORIZED_ACCESS_MESSAGE, is_username_allowed
from app.core.config import Settings
from app.db.repositories import UserSessionRepository
from app.llm.answer import LLMAnswerError, OpenAILLMAnswerer, build_fallback_answer
from app.llm.dictionary import Intent
from app.llm.input import build_llm_input
from app.llm.parser import LLMParserError, OpenAILLMParser
from app.pipeline.admin_debug import is_admin_debug_enabled, send_admin_debug
from app.pipeline.calculation_engine import CalculationEngine, CalculationError
from app.pipeline.command_flow import handle_bot_command
from app.pipeline.context_resolver import empty_dialog_state, resolve_context, set_clarification_state
from app.pipeline.domain_resolver import DomainResolver
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    CONTEXT_BLOCKED_MESSAGE,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    block_short_followup_after_error,
    build_failed_query_state,
)
from app.pipeline.forced_corrections import build_forced_parsed_response
from app.pipeline.guarded_requests import detect_guarded_non_data_request
from app.pipeline.llm_postprocess import (
    apply_article_clarification_selection,
    apply_dimension_clarification_selection,
    apply_dimension_query_fallback,
)
from app.pipeline.logging_context import build_request_log_context, dump_log_context
from app.pipeline.math_shortcuts import resolve_math_shortcut, resolve_pending_math_shortcut
from app.pipeline.metric_resolver import REPORT_NOT_CONNECTED_MESSAGE, resolve_metrics
from app.pipeline.non_data_flow import handle_general_question, handle_guarded_non_data_request, handle_unsupported_query
from app.pipeline.pdf_report import PDF_REPORT_NOTICE, build_pdf_report, should_send_pdf_report
from app.pipeline.pending_actions import PENDING_SHOW_AVAILABLE_ARTICLES
from app.pipeline.pending_flow import handle_pending_action
from app.pipeline.query_frame import NON_DATA_QUERY_MESSAGE, build_query_frame
from app.pipeline.report_compatibility import check_report_compatibility
from app.pipeline.report_semantics import apply_report_semantics
from app.pipeline.response_data import build_response_data
from app.pipeline.result_verifier import verify_result
from app.pipeline.session_state import preserve_admin_debug_flag, user_session_with_state
from app.pipeline.sql_compiler import SQLCompileError, compile_sql
from app.pipeline.text_intents import is_capabilities_question, is_report_type_not_connected, should_skip_pdf_report
from app.pipeline.timing import record_timing
from app.reports.model.catalog import MODEL_RAW_VIEWS


logger = logging.getLogger("formcity.webhook")
LLM_PARSE_ERROR_MESSAGE = NON_DATA_QUERY_MESSAGE


async def process_telegram_webhook(
    request: Request,
    settings: Settings,
    telegram_client: TelegramClient,
    user_session_repository: UserSessionRepository,
    llm_parser: OpenAILLMParser,
    llm_answerer: OpenAILLMAnswerer,
    domain_resolver: DomainResolver,
    calculation_engine: CalculationEngine,
) -> dict[str, object]:
    request_id = str(uuid4())
    request_started_at = perf_counter()
    timings: dict[str, int] = {}
    typing_task: asyncio.Task[None] | None = None
    payload = await request.json()

    try:
        update = TelegramUpdate.model_validate(payload)
    except ValidationError as error:
        logger.warning(
            "invalid_update request_id=%s errors=%s",
            request_id,
            error.errors(),
        )
        return {"ok": False, "request_id": request_id, "error": "invalid_update"}

    message = update.message or update.edited_message
    if message is None:
        logger.info(
            "ignored_update request_id=%s update_id=%s",
            request_id,
            update.update_id,
        )
        return {"ok": True, "request_id": request_id, "ignored": True}

    user = message.from_user
    username = user.username if user else None
    logger.info(
        "telegram_update request_id=%s update_id=%s chat_id=%s username=%s message_id=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        message.message_id,
    )

    if not is_username_allowed(username, settings.allowed_usernames | settings.admin_usernames):
        await safe_send_message(
            telegram_client,
            message.chat.id,
            UNAUTHORIZED_ACCESS_MESSAGE,
            request_id,
        )
        logger.info(
            "access_denied request_id=%s update_id=%s chat_id=%s username=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
        )
        return {
            "ok": True,
            "request_id": request_id,
            "access": "denied",
        }

    user_session = user_session_repository.load_or_create(username, message.chat.id)
    current_state = dict(user_session.state or {})
    user_session_repository.add_user_message(
        user_id=user_session.user.id,
        request_id=request_id,
        update_id=update.update_id,
        telegram_message_id=message.message_id,
        text=message.text,
    )

    command = normalize_command(message.text)
    command_response = await handle_bot_command(
        command,
        username=username,
        chat_id=message.chat.id,
        update_id=update.update_id,
        request_id=request_id,
        user_id=user_session.user.id,
        current_state=current_state,
        settings=settings,
        telegram_client=telegram_client,
        user_session_repository=user_session_repository,
    )
    if command_response is not None:
        return command_response

    pending_response, current_state = await handle_pending_action(
        current_state,
        text=message.text,
        chat_id=message.chat.id,
        user_id=user_session.user.id,
        request_id=request_id,
        telegram_client=telegram_client,
        user_session_repository=user_session_repository,
        domain_resolver=domain_resolver,
    )
    if pending_response is not None:
        return pending_response

    guarded_message = detect_guarded_non_data_request(message.text, current_state=current_state)
    if guarded_message is not None:
        admin_debug_enabled = is_admin_debug_enabled(username, settings, current_state)
        return await handle_guarded_non_data_request(
            message_text=guarded_message,
            chat_id=message.chat.id,
            update_id=update.update_id,
            message_id=message.message_id,
            username=username,
            request_id=request_id,
            user_id=user_session.user.id,
            current_state=current_state,
            timings=timings,
            request_started_at=request_started_at,
            admin_debug_enabled=admin_debug_enabled,
            telegram_client=telegram_client,
            user_session_repository=user_session_repository,
        )

    current_state, forced_parsed_response = build_forced_parsed_response(current_state, message.text)
    if forced_parsed_response is None and block_short_followup_after_error(current_state, message.text):
        state_to_save = preserve_admin_debug_flag(current_state, dict(current_state))
        state_to_save["last_trace"] = jsonable_encoder(
            {
                "request_id": request_id,
                "context_blocked_after_error": True,
                "telegram_response_sent": True,
                "timings": timings,
            },
        )
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(state_to_save),
        )
        telegram_response_sent = await safe_send_message(
            telegram_client,
            message.chat.id,
            CONTEXT_BLOCKED_MESSAGE,
            request_id,
        )
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "update_id": update.update_id,
            "message_id": message.message_id,
            "username": username,
            "access": "allowed",
            "session": "loaded",
            "context_blocked_after_error": True,
            "telegram_response_sent": telegram_response_sent,
            "state_saved": True,
            "timings": timings,
        }

    admin_debug_enabled = is_admin_debug_enabled(username, settings, current_state)

    await safe_send_chat_action(telegram_client, message.chat.id, CHAT_ACTION_TYPING, request_id)
    typing_task = asyncio.create_task(
        keep_chat_action(telegram_client, message.chat.id, CHAT_ACTION_TYPING, request_id),
    )

    pending_math_operation = current_state.get("pending_math_shortcut")
    math_shortcut = None
    math_shortcut_from_pending = False
    if forced_parsed_response is None:
        if isinstance(pending_math_operation, dict):
            math_shortcut = resolve_pending_math_shortcut(message.text, user_session.last_result, pending_math_operation)
            math_shortcut_from_pending = math_shortcut.handled
        if math_shortcut is None or not math_shortcut.handled:
            math_shortcut = resolve_math_shortcut(message.text, user_session.last_result)
    if math_shortcut and math_shortcut.handled:
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "01 MathShortcut",
            math_shortcut,
        )
        state_to_save = preserve_admin_debug_flag(current_state, current_state)
        if math_shortcut_from_pending or math_shortcut.result is not None:
            state_to_save.pop("pending_math_shortcut", None)
        elif math_shortcut.pending_operation is not None:
            state_to_save["pending_math_shortcut"] = math_shortcut.pending_operation
        state_to_save["last_trace"] = jsonable_encoder(
            {
                "request_id": request_id,
                "intent": "math_shortcut",
                "telegram_response_sent": bool(math_shortcut.text),
                "timings": timings,
            },
        )
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(state_to_save),
        )
        last_result_saved = False
        if math_shortcut.result is not None:
            user_session_repository.save_last_result(
                user_session.user.id,
                jsonable_encoder(math_shortcut.result),
                {"source": "math_shortcut", "operation": math_shortcut.result.operation},
            )
            last_result_saved = True
        await stop_background_task(typing_task)
        telegram_response_sent = False
        if math_shortcut.text:
            stage_started_at = perf_counter()
            telegram_response_sent = await safe_send_message(
                telegram_client,
                message.chat.id,
                math_shortcut.text,
                request_id,
            )
            record_timing(timings, "telegram_send", stage_started_at)
            if telegram_response_sent:
                user_session_repository.add_assistant_message(
                    user_session.user.id,
                    request_id,
                    update.update_id,
                    math_shortcut.text,
                )
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "session": "loaded",
            "math_shortcut": "handled",
            "telegram_response_sent": telegram_response_sent,
            "state_saved": True,
            "last_result_saved": last_result_saved,
            "assistant_message_saved": telegram_response_sent,
            "timings": timings,
        }

    if forced_parsed_response is None:
        stage_started_at = perf_counter()
        effective_user_session = user_session_with_state(user_session, current_state)
        llm_input = build_llm_input(message.text, effective_user_session)
        record_timing(timings, "llm_input", stage_started_at)
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "01 LLMInput",
            llm_input,
        )
        logger.info(
            "llm_input_built request_id=%s update_id=%s chat_id=%s username=%s history_size=%s has_last_result=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            len(llm_input.history),
            llm_input.last_result_summary is not None,
        )
        stage_started_at = perf_counter()
        try:
            parsed_response = await llm_parser.parse(llm_input)
        except LLMParserError:
            record_timing(timings, "llm_parse", stage_started_at)
            await stop_background_task(typing_task)
            logger.exception(
                "llm_parse_failed request_id=%s update_id=%s chat_id=%s username=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
            )
            await safe_send_message(
                telegram_client,
                message.chat.id,
                LLM_PARSE_ERROR_MESSAGE,
                request_id,
            )
            record_timing(timings, "total", request_started_at)
            return {
                "ok": True,
                "request_id": request_id,
                "access": "allowed",
                "llm_parse": "failed",
                "timings": timings,
            }
        record_timing(timings, "llm_parse", stage_started_at)
        parsed_response = apply_article_clarification_selection(current_state, parsed_response, message.text)
        parsed_response = apply_dimension_clarification_selection(current_state, parsed_response, message.text)
        parsed_response = apply_dimension_query_fallback(parsed_response, message.text)
    else:
        parsed_response = forced_parsed_response
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "01 FailedQueryCorrection",
            {
                "text": message.text,
                "state": current_state,
                "parsed_response": parsed_response,
            },
        )

    logger.info(
        "llm_parse_done request_id=%s update_id=%s chat_id=%s username=%s intent=%s confidence=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        parsed_response.intent,
        parsed_response.confidence,
    )
    logger.info(
        "llm_parsed_payload request_id=%s update_id=%s chat_id=%s username=%s payload=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        json.dumps(jsonable_encoder(parsed_response), ensure_ascii=False, sort_keys=True),
    )
    await send_admin_debug(
        telegram_client,
        message.chat.id,
        request_id,
        admin_debug_enabled,
        "02 LLMParsedResponse",
        parsed_response,
    )

    if parsed_response.intent == Intent.GENERAL_QUESTION or (
        parsed_response.intent == Intent.UNSUPPORTED and is_capabilities_question(message.text)
    ):
        return await handle_general_question(
            parsed_response,
            text=message.text,
            chat_id=message.chat.id,
            update_id=update.update_id,
            message_id=message.message_id,
            username=username,
            request_id=request_id,
            user_id=user_session.user.id,
            current_state=current_state,
            timings=timings,
            request_started_at=request_started_at,
            typing_task=typing_task,
            admin_debug_enabled=admin_debug_enabled,
            telegram_client=telegram_client,
            user_session_repository=user_session_repository,
            llm_answerer=llm_answerer,
        )

    if parsed_response.intent == Intent.UNSUPPORTED:
        return await handle_unsupported_query(
            parsed_response,
            chat_id=message.chat.id,
            update_id=update.update_id,
            message_id=message.message_id,
            username=username,
            request_id=request_id,
            user_id=user_session.user.id,
            current_state=current_state,
            timings=timings,
            request_started_at=request_started_at,
            typing_task=typing_task,
            admin_debug_enabled=admin_debug_enabled,
            telegram_client=telegram_client,
            user_session_repository=user_session_repository,
        )

    stage_started_at = perf_counter()
    resolved_state = resolve_context(current_state, parsed_response)
    record_timing(timings, "context", stage_started_at)
    await send_admin_debug(
        telegram_client,
        message.chat.id,
        request_id,
        admin_debug_enabled,
        "03 DialogState",
        resolved_state,
    )
    logger.info(
        "context_resolved request_id=%s update_id=%s chat_id=%s username=%s intent=%s awaiting_clarification=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        resolved_state["last_intent"],
        resolved_state["awaiting_clarification"],
    )
    stage_started_at = perf_counter()
    query_frame = apply_report_semantics(build_query_frame(resolved_state))
    resolved_state["metrics"] = query_frame.metrics
    resolved_state["filters"] = query_frame.filters
    resolved_state["group_by"] = query_frame.group_by
    resolved_state["view"] = query_frame.view
    record_timing(timings, "query_frame", stage_started_at)
    await send_admin_debug(
        telegram_client,
        message.chat.id,
        request_id,
        admin_debug_enabled,
        "04 QueryFrame",
        query_frame,
    )
    logger.info(
        "query_frame_built request_id=%s update_id=%s chat_id=%s username=%s ready=%s missing_fields=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        query_frame.ready,
        query_frame.missing_fields,
    )
    if is_report_type_not_connected(query_frame.report_type):
        state_to_save = preserve_admin_debug_flag(current_state, empty_dialog_state())
        state_to_save["last_trace"] = jsonable_encoder(
            {
                "request_id": request_id,
                "intent": parsed_response.intent,
                "query_ready": False,
                "metrics_valid": False,
                "metric_errors": ["report_type_not_connected"],
                "telegram_response_sent": True,
                "timings": timings,
            },
        )
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(state_to_save),
        )
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "05 ReportNotConnected",
            {
                "report_type": query_frame.report_type,
                "metric_errors": ["report_type_not_connected"],
                "response": REPORT_NOT_CONNECTED_MESSAGE,
            },
        )
        await stop_background_task(typing_task)
        stage_started_at = perf_counter()
        telegram_response_sent = await safe_send_message(
            telegram_client,
            message.chat.id,
            REPORT_NOT_CONNECTED_MESSAGE,
            request_id,
        )
        record_timing(timings, "telegram_send", stage_started_at)
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "update_id": update.update_id,
            "message_id": message.message_id,
            "username": username,
            "access": "allowed",
            "session": "loaded",
            "llm_input": "built",
            "llm_parse": "done",
            "context": "resolved",
            "query_frame": "built",
            "query_ready": False,
            "missing_fields": [],
            "metrics_valid": False,
            "metric_errors": ["report_type_not_connected"],
            "telegram_response_sent": telegram_response_sent,
            "state_saved": True,
            "intent": parsed_response.intent,
            "timings": timings,
        }

    compatibility_check = check_report_compatibility(query_frame, message.text)
    if not compatibility_check.valid:
        state_to_save = preserve_admin_debug_flag(current_state, dict(current_state))
        state_to_save[CONTEXT_BLOCKED_AFTER_ERROR] = True
        state_to_save[FAILED_QUERY_ERROR] = compatibility_check.error
        state_to_save[FAILED_QUERY_STATE] = jsonable_encoder(
            build_failed_query_state(current_state, resolved_state, compatibility_check.error),
        )
        state_to_save["last_trace"] = jsonable_encoder(
            {
                "request_id": request_id,
                "intent": parsed_response.intent,
                "query_ready": False,
                "compatibility_valid": False,
                "compatibility_error": compatibility_check.error,
                "context_blocked_after_error": True,
                "failed_query_state_saved": True,
                "telegram_response_sent": True,
                "timings": timings,
            },
        )
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(state_to_save),
        )
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "05 CompatibilityCheck",
            compatibility_check,
        )
        await stop_background_task(typing_task)
        stage_started_at = perf_counter()
        telegram_response_sent = await safe_send_message(
            telegram_client,
            message.chat.id,
            compatibility_check.message or NON_DATA_QUERY_MESSAGE,
            request_id,
        )
        record_timing(timings, "telegram_send", stage_started_at)
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "update_id": update.update_id,
            "message_id": message.message_id,
            "username": username,
            "access": "allowed",
            "session": "loaded",
            "llm_input": "built",
            "llm_parse": "done",
            "context": "resolved",
            "query_frame": "built",
            "query_ready": False,
            "missing_fields": [],
            "compatibility_valid": False,
            "compatibility_error": compatibility_check.error,
            "telegram_response_sent": telegram_response_sent,
            "state_saved": True,
            "intent": parsed_response.intent,
            "timings": timings,
        }

    stage_started_at = perf_counter()
    domain_resolution = domain_resolver.resolve(query_frame)
    query_frame = domain_resolution.frame
    resolved_state["period"] = query_frame.period.model_dump(by_alias=True)
    resolved_state["filters"] = query_frame.filters
    resolved_state["group_by"] = query_frame.group_by
    resolved_state["view"] = query_frame.view
    record_timing(timings, "domain", stage_started_at)
    logger.info(
        "domain_resolved request_id=%s update_id=%s chat_id=%s username=%s valid=%s errors=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        domain_resolution.valid,
        domain_resolution.errors,
    )
    await send_admin_debug(
        telegram_client,
        message.chat.id,
        request_id,
        admin_debug_enabled,
        "05 DomainResolution",
        {
            "valid": domain_resolution.valid,
            "errors": domain_resolution.errors,
            "clarification_question": domain_resolution.clarification_question,
            "query_frame": query_frame,
        },
    )
    if not domain_resolution.valid:
        if "period_data_not_found" in domain_resolution.errors:
            state_to_save = dict(current_state)
        elif "article_not_found" in domain_resolution.errors:
            state_to_save = dict(resolved_state)
            filters = dict(state_to_save.get("filters") or {})
            missing_article = filters.get("article")
            state_to_save["filters"] = filters
            state_to_save[CONTEXT_BLOCKED_AFTER_ERROR] = True
            state_to_save[FAILED_QUERY_ERROR] = "article_not_found"
            state_to_save[FAILED_QUERY_STATE] = jsonable_encoder(build_failed_query_state(current_state, resolved_state, "article_not_found"))
            state_to_save["awaiting_clarification"] = False
            state_to_save["clarification_target"] = None
            state_to_save["clarification_base_state"] = None
            state_to_save["pending_action"] = PENDING_SHOW_AVAILABLE_ARTICLES
            state_to_save["pending_payload"] = {
                "report_type": query_frame.report_type,
                "project": query_frame.project,
                "period": query_frame.period.model_dump(by_alias=True),
                "missing_article": missing_article,
            }
        elif "article_ambiguous" in domain_resolution.errors:
            state_to_save = set_clarification_state(
                resolved_state,
                domain_resolution.clarification_question,
                kind=str(domain_resolution.details.get("clarification_kind") or "article"),
                options=[
                    option
                    for option in domain_resolution.details.get("article_candidates", [])
                    if isinstance(option, str)
                ],
            )
        else:
            state_to_save = set_clarification_state(resolved_state, domain_resolution.clarification_question)
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(preserve_admin_debug_flag(current_state, state_to_save)),
        )
        await stop_background_task(typing_task)
        if domain_resolution.clarification_question:
            stage_started_at = perf_counter()
            await safe_send_message(
                telegram_client,
                message.chat.id,
                domain_resolution.clarification_question,
                request_id,
            )
            record_timing(timings, "telegram_send", stage_started_at)
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "update_id": update.update_id,
            "message_id": message.message_id,
            "username": username,
            "access": "allowed",
            "session": "loaded",
            "llm_input": "built",
            "llm_parse": "done",
            "context": "resolved",
            "query_frame": "built",
            "query_ready": query_frame.ready,
            "missing_fields": query_frame.missing_fields,
            "domain_valid": False,
            "domain_errors": domain_resolution.errors,
            "telegram_response_sent": bool(domain_resolution.clarification_question),
            "state_saved": True,
            "intent": parsed_response.intent,
            "timings": timings,
        }

    if not query_frame.ready:
        if "dimension" in query_frame.missing_fields:
            clarification_kind = "dimension"
        elif "report_type" in query_frame.missing_fields:
            clarification_kind = "report_type"
        else:
            clarification_kind = None
        resolved_state = set_clarification_state(
            resolved_state,
            query_frame.clarification_question,
            kind=clarification_kind,
        )
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(preserve_admin_debug_flag(current_state, resolved_state)),
        )
        await stop_background_task(typing_task)
        if query_frame.clarification_question:
            stage_started_at = perf_counter()
            await safe_send_message(
                telegram_client,
                message.chat.id,
                query_frame.clarification_question,
                request_id,
            )
            record_timing(timings, "telegram_send", stage_started_at)
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "update_id": update.update_id,
            "message_id": message.message_id,
            "username": username,
            "access": "allowed",
            "session": "loaded",
            "llm_input": "built",
            "llm_parse": "done",
            "context": "resolved",
            "query_frame": "built",
            "query_ready": False,
            "missing_fields": query_frame.missing_fields,
            "telegram_response_sent": bool(query_frame.clarification_question),
            "state_saved": True,
            "intent": parsed_response.intent,
            "timings": timings,
        }

    stage_started_at = perf_counter()
    metric_resolution = resolve_metrics(query_frame)
    record_timing(timings, "metrics", stage_started_at)
    await send_admin_debug(
        telegram_client,
        message.chat.id,
        request_id,
        admin_debug_enabled,
        "06 MetricResolution",
        metric_resolution,
    )
    logger.info(
        "metrics_resolved request_id=%s update_id=%s chat_id=%s username=%s valid=%s errors=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        metric_resolution.valid,
        metric_resolution.errors,
    )
    if not metric_resolution.valid:
        if {"report_type_not_connected", "metric_not_allowed_for_report_type"} & set(metric_resolution.errors):
            state_to_save = preserve_admin_debug_flag(current_state, empty_dialog_state())
        else:
            resolved_state = set_clarification_state(resolved_state, metric_resolution.clarification_question)
            state_to_save = preserve_admin_debug_flag(current_state, resolved_state)
        state_to_save["last_trace"] = jsonable_encoder(
            {
                "request_id": request_id,
                "intent": parsed_response.intent,
                "query_ready": query_frame.ready,
                "metrics_valid": False,
                "metric_errors": metric_resolution.errors,
                "telegram_response_sent": bool(metric_resolution.clarification_question),
                "timings": timings,
            },
        )
        user_session_repository.save_dialog_state(
            user_session.user.id,
            jsonable_encoder(state_to_save),
        )
        await stop_background_task(typing_task)
        telegram_response_sent = False
        if metric_resolution.clarification_question:
            stage_started_at = perf_counter()
            telegram_response_sent = await safe_send_message(
                telegram_client,
                message.chat.id,
                metric_resolution.clarification_question,
                request_id,
            )
            record_timing(timings, "telegram_send", stage_started_at)
        record_timing(timings, "total", request_started_at)
        return {
            "ok": True,
            "request_id": request_id,
            "update_id": update.update_id,
            "message_id": message.message_id,
            "username": username,
            "access": "allowed",
            "session": "loaded",
            "llm_input": "built",
            "llm_parse": "done",
            "context": "resolved",
            "query_frame": "built",
            "query_ready": query_frame.ready,
            "missing_fields": query_frame.missing_fields,
            "metrics_valid": False,
            "metric_errors": metric_resolution.errors,
            "telegram_response_sent": telegram_response_sent,
            "state_saved": True,
            "intent": parsed_response.intent,
            "timings": timings,
        }

    sql_query = None
    sql_error = None
    should_compile_sql = query_frame.ready and metric_resolution.valid and (
        bool(metric_resolution.metrics) or query_frame.intent == "dimension_query"
        or (query_frame.report_type == "model" and query_frame.view in MODEL_RAW_VIEWS)
    )
    if should_compile_sql:
        stage_started_at = perf_counter()
        try:
            sql_query = compile_sql(query_frame, metric_resolution)
        except SQLCompileError as error:
            record_timing(timings, "sql", stage_started_at)
            sql_error = str(error)
            logger.warning(
                "sql_compile_failed request_id=%s update_id=%s chat_id=%s username=%s error=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                sql_error,
            )
        else:
            record_timing(timings, "sql", stage_started_at)
            logger.info(
                "sql_compiled request_id=%s update_id=%s chat_id=%s username=%s table=%s metrics=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                sql_query.table,
                sql_query.metrics,
            )
            await send_admin_debug(
                telegram_client,
                message.chat.id,
                request_id,
                admin_debug_enabled,
                "07 SQLQuery",
                sql_query,
            )
    calculation_result = None
    calculation_error = None
    if query_frame.ready and metric_resolution.valid and (sql_query is not None or query_frame.operation):
        stage_started_at = perf_counter()
        try:
            calculation_result = calculation_engine.calculate(
                query_frame,
                sql_query,
                user_session.last_result,
            )
        except CalculationError as error:
            record_timing(timings, "calculation", stage_started_at)
            calculation_error = str(error)
            logger.warning(
                "calculation_failed request_id=%s update_id=%s chat_id=%s username=%s error=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                calculation_error,
            )
        else:
            record_timing(timings, "calculation", stage_started_at)
            logger.info(
                "calculation_done request_id=%s update_id=%s chat_id=%s username=%s kind=%s row_count=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                calculation_result.kind,
                calculation_result.row_count,
            )
            await send_admin_debug(
                telegram_client,
                message.chat.id,
                request_id,
                admin_debug_enabled,
                "08 CalculationResult",
                calculation_result,
            )
    result_verification = None
    if query_frame.ready and metric_resolution.valid:
        stage_started_at = perf_counter()
        result_verification = verify_result(
            query_frame,
            metric_resolution,
            calculation_result,
        )
        record_timing(timings, "verification", stage_started_at)
        logger.info(
            "result_verified request_id=%s update_id=%s chat_id=%s username=%s verified=%s errors=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            result_verification.verified,
            result_verification.errors,
        )
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "09 ResultVerification",
            result_verification,
        )
    response_data = None
    if result_verification is not None:
        stage_started_at = perf_counter()
        response_data = build_response_data(calculation_result, result_verification)
        record_timing(timings, "response_data", stage_started_at)
        logger.info(
            "response_data_built request_id=%s update_id=%s chat_id=%s username=%s ready=%s errors=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            response_data.ready,
            response_data.errors,
        )
        await send_admin_debug(
            telegram_client,
            message.chat.id,
            request_id,
            admin_debug_enabled,
            "10 ResponseData",
            response_data,
        )
    pdf_error = None
    telegram_response_status = None
    if (
        response_data is not None
        and response_data.ready
        and result_verification is not None
        and telegram_response_status is None
        and not should_skip_pdf_report(response_data)
        and should_send_pdf_report(calculation_result)
    ):
        try:
            stage_started_at = perf_counter()
            pdf_bytes, pdf_filename = build_pdf_report(calculation_result, result_verification)
            record_timing(timings, "pdf", stage_started_at)
            await stop_background_task(typing_task)
            await safe_send_chat_action(telegram_client, message.chat.id, CHAT_ACTION_UPLOAD_DOCUMENT, request_id)
            stage_started_at = perf_counter()
            await safe_send_message(telegram_client, message.chat.id, PDF_REPORT_NOTICE, request_id)
            await telegram_client.send_document(
                message.chat.id,
                pdf_bytes,
                pdf_filename,
                caption="Готовый отчет в PDF.",
            )
            record_timing(timings, "telegram_send", stage_started_at)
            telegram_response_status = TelegramResponseStatus(sent=True, chunks=2)
        except Exception as error:
            await stop_background_task(typing_task)
            pdf_error = type(error).__name__
            logger.warning(
                "pdf_report_failed request_id=%s update_id=%s chat_id=%s username=%s error=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                pdf_error,
            )
        else:
            logger.info(
                "pdf_report_sent request_id=%s update_id=%s chat_id=%s username=%s filename=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                pdf_filename,
            )
            await send_admin_debug(
                telegram_client,
                message.chat.id,
                request_id,
                admin_debug_enabled,
                "11 PDFReport",
                {"filename": pdf_filename, "bytes": len(pdf_bytes), "sent": True},
            )
    answer_draft = None
    answer_error = None
    if response_data is not None and telegram_response_status is None:
        stage_started_at = perf_counter()
        try:
            answer_draft = await llm_answerer.build_answer(response_data)
        except LLMAnswerError as error:
            record_timing(timings, "llm_answer", stage_started_at)
            answer_error = str(error)
            answer_draft = build_fallback_answer(response_data)
            logger.warning(
                "llm_answer_failed request_id=%s update_id=%s chat_id=%s username=%s error=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                answer_error,
            )
        else:
            record_timing(timings, "llm_answer", stage_started_at)
            logger.info(
                "llm_answer_done request_id=%s update_id=%s chat_id=%s username=%s used_metrics=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                answer_draft.used_metrics,
            )
            await send_admin_debug(
                telegram_client,
                message.chat.id,
                request_id,
                admin_debug_enabled,
                "11 AnswerDraft",
                answer_draft,
            )
    if answer_draft is not None:
        source = response_data.source if response_data is not None else {}
        if (
            isinstance(source, dict)
            and source.get("report_type") == "model"
            and source.get("view") in MODEL_RAW_VIEWS
        ):
            user_session_repository.save_dialog_state(
                user_session.user.id,
                jsonable_encoder(preserve_admin_debug_flag(current_state, resolved_state)),
            )
        await stop_background_task(typing_task)
        stage_started_at = perf_counter()
        telegram_response_status = await send_answer_to_telegram(
            telegram_client,
            message.chat.id,
            answer_draft,
        )
        record_timing(timings, "telegram_send", stage_started_at)
        logger.info(
            "telegram_response_sent request_id=%s update_id=%s chat_id=%s username=%s sent=%s chunks=%s error=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            telegram_response_status.sent,
            telegram_response_status.chunks,
            telegram_response_status.error,
        )
    await stop_background_task(typing_task)
    await send_admin_debug(
        telegram_client,
        message.chat.id,
        request_id,
        admin_debug_enabled,
        "12 TelegramResponseStatus",
        telegram_response_status,
    )
    trace = {
        "request_id": request_id,
        "intent": parsed_response.intent,
        "query_ready": query_frame.ready,
        "metrics_valid": metric_resolution.valid,
        "sql_compiled": sql_query is not None,
        "calculation_done": calculation_result is not None,
        "result_verified": result_verification.verified if result_verification else False,
        "response_data_ready": response_data.ready if response_data else False,
            "llm_answer_done": answer_draft is not None,
            "telegram_response_sent": telegram_response_status.sent if telegram_response_status else False,
            "timings": timings,
        }
    state_to_save = preserve_admin_debug_flag(current_state, resolved_state)
    state_to_save["last_trace"] = jsonable_encoder(trace)
    user_session_repository.save_dialog_state(
        user_session.user.id,
        jsonable_encoder(state_to_save),
    )
    state_saved = True

    last_result_saved = False
    if calculation_result is not None and result_verification is not None and result_verification.verified:
        user_session_repository.save_last_result(
            user_session.user.id,
            jsonable_encoder(calculation_result),
            jsonable_encoder(query_frame.model_dump(by_alias=True)),
        )
        last_result_saved = True

    assistant_message_saved = False
    if answer_draft is not None and telegram_response_status is not None and telegram_response_status.sent:
        user_session_repository.add_assistant_message(
            user_session.user.id,
            request_id,
            update.update_id,
            answer_draft.text,
        )
        assistant_message_saved = True
    logger.info(
        "state_saved request_id=%s update_id=%s chat_id=%s username=%s state_saved=%s last_result_saved=%s assistant_message_saved=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        state_saved,
        last_result_saved,
        assistant_message_saved,
    )
    request_log_context = build_request_log_context(
        request_id=request_id,
        username=username,
        update_id=update.update_id,
        chat_id=message.chat.id,
        query_frame=query_frame,
        statuses={
            "query_ready": query_frame.ready,
            "metrics_valid": metric_resolution.valid,
            "sql_compiled": sql_query is not None,
            "calculation_done": calculation_result is not None,
            "result_verified": result_verification.verified if result_verification else False,
            "response_data_ready": response_data.ready if response_data else False,
            "llm_answer_done": answer_draft is not None,
            "telegram_response_sent": telegram_response_status.sent if telegram_response_status else False,
            "state_saved": state_saved,
            "last_result_saved": last_result_saved,
            "assistant_message_saved": assistant_message_saved,
        },
        errors={
            "metric_errors": metric_resolution.errors,
            "sql_error": sql_error,
            "calculation_error": calculation_error,
            "result_errors": result_verification.errors if result_verification else [],
            "response_data_errors": response_data.errors if response_data else [],
            "llm_answer_error": answer_error,
            "pdf_error": pdf_error,
            "telegram_response_error": telegram_response_status.error if telegram_response_status else None,
        },
    )
    record_timing(timings, "total", request_started_at)
    logger.info(
        "request_timings request_id=%s update_id=%s chat_id=%s username=%s timings=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        json.dumps(timings, ensure_ascii=False, sort_keys=True),
    )
    logger.info("request_completed %s", dump_log_context(request_log_context))

    return {
        "ok": True,
        "request_id": request_id,
        "update_id": update.update_id,
        "message_id": message.message_id,
        "username": username,
        "access": "allowed",
        "session": "loaded",
        "llm_input": "built",
        "llm_parse": "done",
        "context": "resolved",
        "query_frame": "built",
        "query_ready": query_frame.ready,
        "missing_fields": query_frame.missing_fields,
        "metrics_valid": metric_resolution.valid,
        "metric_errors": metric_resolution.errors,
        "sql_compiled": sql_query is not None,
        "sql_error": sql_error,
        "calculation_done": calculation_result is not None,
        "calculation_error": calculation_error,
        "result_verified": result_verification.verified if result_verification else False,
        "result_errors": result_verification.errors if result_verification else [],
        "response_data_ready": response_data.ready if response_data else False,
        "response_data_errors": response_data.errors if response_data else [],
        "llm_answer": "done" if answer_draft else "skipped",
        "llm_answer_error": answer_error,
        "pdf_error": pdf_error,
        "telegram_response_sent": telegram_response_status.sent if telegram_response_status else False,
        "telegram_response_chunks": telegram_response_status.chunks if telegram_response_status else 0,
        "telegram_response_error": telegram_response_status.error if telegram_response_status else None,
        "state_saved": state_saved,
        "last_result_saved": last_result_saved,
        "assistant_message_saved": assistant_message_saved,
        "intent": parsed_response.intent,
        "timings": timings,
    }
