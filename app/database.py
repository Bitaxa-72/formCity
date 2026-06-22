from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import Base


@lru_cache
def get_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


@lru_cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), autoflush=False, expire_on_commit=False)


def create_database_tables(database_url: str) -> None:
    Base.metadata.create_all(bind=get_engine(database_url))


def get_db_session(settings: Settings) -> Generator[Session, None, None]:
    session_factory = get_session_factory(settings.database_url)
    with session_factory() as session:
        yield session
