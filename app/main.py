import logging

from fastapi import Depends, FastAPI, Request

from app.bot.commands import BOT_COMMANDS
from app.bot.telegram_client import TelegramClient
from app.core.config import Settings
from app.dependencies import (
    get_calculation_engine,
    get_domain_resolver,
    get_health_checker,
    get_llm_answerer,
    get_llm_parser,
    get_settings,
    get_telegram_client,
    get_user_session_repository,
)
from app.db.repositories import UserSessionRepository
from app.health import HealthChecker
from app.llm.answer import OpenAILLMAnswerer
from app.llm.parser import OpenAILLMParser
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    CONTEXT_BLOCKED_MESSAGE,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
)
from app.pipeline.llm_postprocess import (
    apply_article_clarification_selection,
    apply_dimension_clarification_selection,
    apply_dimension_query_fallback,
)
from app.pipeline.calculation_engine import CalculationEngine
from app.pipeline.domain_resolver import DomainResolver
from app.pipeline.pending_actions import (
    PENDING_CANCEL_MESSAGE,
    PENDING_SHOW_AVAILABLE_ARTICLES,
    PENDING_UNCLEAR_MESSAGE,
)
from app.pipeline.query_frame import NON_DATA_QUERY_MESSAGE
from app.webhook_handler import process_telegram_webhook


LLM_PARSE_ERROR_MESSAGE = NON_DATA_QUERY_MESSAGE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="formCityBot")


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


@app.post("/telegram/commands")
async def setup_telegram_commands(
    telegram_client: TelegramClient = Depends(get_telegram_client),
) -> dict[str, object]:
    result = await telegram_client.set_my_commands(BOT_COMMANDS)
    return {"ok": bool(result.get("ok")), "commands": BOT_COMMANDS}


@app.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    telegram_client: TelegramClient = Depends(get_telegram_client),
    user_session_repository: UserSessionRepository = Depends(get_user_session_repository),
    llm_parser: OpenAILLMParser = Depends(get_llm_parser),
    llm_answerer: OpenAILLMAnswerer = Depends(get_llm_answerer),
    domain_resolver: DomainResolver = Depends(get_domain_resolver),
    calculation_engine: CalculationEngine = Depends(get_calculation_engine),
) -> dict[str, object]:
    return await process_telegram_webhook(
        request=request,
        settings=settings,
        telegram_client=telegram_client,
        user_session_repository=user_session_repository,
        llm_parser=llm_parser,
        llm_answerer=llm_answerer,
        domain_resolver=domain_resolver,
        calculation_engine=calculation_engine,
    )
