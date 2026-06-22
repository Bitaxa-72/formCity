import logging
from collections.abc import Generator
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.access import UNAUTHORIZED_ACCESS_MESSAGE, is_username_allowed
from app.calculation_engine import CalculationEngine, CalculationError
from app.commands import COMMAND_RESPONSES, normalize_command
from app.config import Settings, load_settings
from app.context_resolver import resolve_context
from app.database import create_database_tables, get_db_session
from app.health import HealthChecker
from app.llm_answer import LLMAnswerError, OpenAILLMAnswerer
from app.llm_input import build_llm_input
from app.llm_parser import LLMParserError, OpenAILLMParser
from app.logging_context import build_request_log_context, dump_log_context
from app.metric_resolver import resolve_metrics
from app.query_frame import build_query_frame
from app.repositories import UserSessionRepository
from app.result_verifier import verify_result
from app.response_data import build_response_data
from app.sql_compiler import SQLCompileError, compile_sql
from app.telegram_client import TelegramClient
from app.telegram_response import send_answer_to_telegram
from app.telegram_schemas import TelegramUpdate


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("formcity.webhook")

app = FastAPI(title="formCityBot")
LLM_PARSE_ERROR_MESSAGE = "Не удалось разобрать запрос. Попробуйте сформулировать его точнее."


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


def get_settings() -> Settings:
    return load_settings()


def get_telegram_client(settings: Settings = Depends(get_settings)) -> TelegramClient:
    return TelegramClient(settings.bot_token)


def get_database_session(
    settings: Settings = Depends(get_settings),
) -> Generator[Session, None, None]:
    create_database_tables(settings.database_url)
    yield from get_db_session(settings)


def get_user_session_repository(
    db: Session = Depends(get_database_session),
) -> UserSessionRepository:
    return UserSessionRepository(db)


def get_health_checker(
    settings: Settings = Depends(get_settings),
    telegram_client: TelegramClient = Depends(get_telegram_client),
) -> HealthChecker:
    return HealthChecker(settings, telegram_client)


def get_llm_parser(settings: Settings = Depends(get_settings)) -> OpenAILLMParser:
    return OpenAILLMParser(settings)


def get_llm_answerer(settings: Settings = Depends(get_settings)) -> OpenAILLMAnswerer:
    return OpenAILLMAnswerer(settings)


def get_calculation_engine(
    db: Session = Depends(get_database_session),
) -> CalculationEngine:
    return CalculationEngine(db)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/dependencies")
async def dependency_health(
    health_checker: HealthChecker = Depends(get_health_checker),
) -> dict[str, object]:
    result = await health_checker.check_all()
    return {
        "ok": result.ok,
        "failed_service": result.failed_service,
    }


@app.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    telegram_client: TelegramClient = Depends(get_telegram_client),
    health_checker: HealthChecker = Depends(get_health_checker),
    user_session_repository: UserSessionRepository = Depends(get_user_session_repository),
    llm_parser: OpenAILLMParser = Depends(get_llm_parser),
    llm_answerer: OpenAILLMAnswerer = Depends(get_llm_answerer),
    calculation_engine: CalculationEngine = Depends(get_calculation_engine),
) -> dict[str, object]:
    request_id = str(uuid4())
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

    if not is_username_allowed(username, settings.allowed_usernames):
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
    user_session_repository.add_user_message(
        user_id=user_session.user.id,
        request_id=request_id,
        update_id=update.update_id,
        telegram_message_id=message.message_id,
        text=message.text,
    )

    command = normalize_command(message.text)
    if command:
        if command == "/clear":
            user_session_repository.clear_state(user_session.user.id)

        await safe_send_message(
            telegram_client,
            message.chat.id,
            COMMAND_RESPONSES[command],
            request_id,
        )
        logger.info(
            "command_handled request_id=%s update_id=%s chat_id=%s username=%s command=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            command,
        )
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "command": command,
            "session": "loaded",
        }

    health_result = await health_checker.check_all()
    if not health_result.ok:
        if health_result.user_message:
            await safe_send_message(
                telegram_client,
                message.chat.id,
                health_result.user_message,
                request_id,
            )
        logger.warning(
            "health_check_failed request_id=%s update_id=%s chat_id=%s username=%s service=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            health_result.failed_service,
        )
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "health": "failed",
            "failed_service": health_result.failed_service,
        }

    llm_input = build_llm_input(message.text, user_session)
    logger.info(
        "llm_input_built request_id=%s update_id=%s chat_id=%s username=%s history_size=%s has_last_result=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        len(llm_input.history),
        llm_input.last_result_summary is not None,
    )
    try:
        parsed_response = await llm_parser.parse(llm_input)
    except LLMParserError:
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
        return {
            "ok": True,
            "request_id": request_id,
            "access": "allowed",
            "llm_parse": "failed",
        }

    logger.info(
        "llm_parse_done request_id=%s update_id=%s chat_id=%s username=%s intent=%s confidence=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        parsed_response.intent,
        parsed_response.confidence,
    )
    resolved_state = resolve_context(user_session.state, parsed_response)
    logger.info(
        "context_resolved request_id=%s update_id=%s chat_id=%s username=%s intent=%s awaiting_clarification=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        resolved_state["last_intent"],
        resolved_state["awaiting_clarification"],
    )
    query_frame = build_query_frame(resolved_state)
    logger.info(
        "query_frame_built request_id=%s update_id=%s chat_id=%s username=%s ready=%s missing_fields=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        query_frame.ready,
        query_frame.missing_fields,
    )
    metric_resolution = resolve_metrics(query_frame)
    logger.info(
        "metrics_resolved request_id=%s update_id=%s chat_id=%s username=%s valid=%s errors=%s",
        request_id,
        update.update_id,
        message.chat.id,
        username,
        metric_resolution.valid,
        metric_resolution.errors,
    )
    sql_query = None
    sql_error = None
    if query_frame.ready and metric_resolution.valid and metric_resolution.metrics:
        try:
            sql_query = compile_sql(query_frame, metric_resolution)
        except SQLCompileError as error:
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
            logger.info(
                "sql_compiled request_id=%s update_id=%s chat_id=%s username=%s table=%s metrics=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                sql_query.table,
                sql_query.metrics,
            )
    calculation_result = None
    calculation_error = None
    if query_frame.ready and metric_resolution.valid and (sql_query is not None or query_frame.operation):
        try:
            calculation_result = calculation_engine.calculate(
                query_frame,
                sql_query,
                user_session.last_result,
            )
        except CalculationError as error:
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
            logger.info(
                "calculation_done request_id=%s update_id=%s chat_id=%s username=%s kind=%s row_count=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                calculation_result.kind,
                calculation_result.row_count,
            )
    result_verification = None
    if query_frame.ready and metric_resolution.valid:
        result_verification = verify_result(
            query_frame,
            metric_resolution,
            calculation_result,
        )
        logger.info(
            "result_verified request_id=%s update_id=%s chat_id=%s username=%s verified=%s errors=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            result_verification.verified,
            result_verification.errors,
        )
    response_data = None
    if result_verification is not None:
        response_data = build_response_data(calculation_result, result_verification)
        logger.info(
            "response_data_built request_id=%s update_id=%s chat_id=%s username=%s ready=%s errors=%s",
            request_id,
            update.update_id,
            message.chat.id,
            username,
            response_data.ready,
            response_data.errors,
        )
    answer_draft = None
    answer_error = None
    if response_data is not None:
        try:
            answer_draft = await llm_answerer.build_answer(response_data)
        except LLMAnswerError as error:
            answer_error = str(error)
            logger.warning(
                "llm_answer_failed request_id=%s update_id=%s chat_id=%s username=%s error=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                answer_error,
            )
        else:
            logger.info(
                "llm_answer_done request_id=%s update_id=%s chat_id=%s username=%s used_metrics=%s",
                request_id,
                update.update_id,
                message.chat.id,
                username,
                answer_draft.used_metrics,
            )
    telegram_response_status = None
    if answer_draft is not None:
        telegram_response_status = await send_answer_to_telegram(
            telegram_client,
            message.chat.id,
            answer_draft,
        )
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
    }
    state_to_save = dict(resolved_state)
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
            "telegram_response_error": telegram_response_status.error if telegram_response_status else None,
        },
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
        "telegram_response_sent": telegram_response_status.sent if telegram_response_status else False,
        "telegram_response_chunks": telegram_response_status.chunks if telegram_response_status else 0,
        "telegram_response_error": telegram_response_status.error if telegram_response_status else None,
        "state_saved": state_saved,
        "last_result_saved": last_result_saved,
        "assistant_message_saved": assistant_message_saved,
        "intent": parsed_response.intent,
    }
