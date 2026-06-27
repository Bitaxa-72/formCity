from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bot.telegram_client import TelegramClient
from app.core.config import Settings, load_settings
from app.db.database import create_database_tables, get_db_session
from app.db.repositories import UserSessionRepository
from app.health import HealthChecker
from app.llm.answer import OpenAILLMAnswerer
from app.llm.parser import OpenAILLMParser
from app.pipeline.calculation_engine import CalculationEngine
from app.pipeline.domain_resolver import DomainResolver


def get_settings() -> Settings:
    return load_settings()


def get_telegram_client(settings: Settings = Depends(get_settings)) -> TelegramClient:
    return TelegramClient(settings.bot_token, settings.telegram_proxy)


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


def get_domain_resolver(
    db: Session = Depends(get_database_session),
) -> DomainResolver:
    return DomainResolver(db)
