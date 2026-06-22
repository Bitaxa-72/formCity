from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import Base, DialogState, LastResult
from app.repositories import UserSessionRepository


def create_repository() -> UserSessionRepository:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return UserSessionRepository(session_factory())


def test_load_or_create_creates_user_and_empty_state() -> None:
    repository = create_repository()

    user_session = repository.load_or_create("Tester", 777)

    assert user_session.user.username == "tester"
    assert user_session.user.telegram_chat_id == 777
    assert user_session.state == {}
    assert user_session.history == []
    assert user_session.last_result is None


def test_add_user_message_saves_history() -> None:
    repository = create_repository()
    user_session = repository.load_or_create("tester", 777)

    repository.add_user_message(
        user_id=user_session.user.id,
        request_id="request-id",
        update_id=1001,
        telegram_message_id=55,
        text="Привет",
    )
    loaded = repository.load_or_create("tester", 777)

    assert len(loaded.history) == 1
    assert loaded.history[0].text == "Привет"
    assert loaded.history[0].request_id == "request-id"


def test_add_assistant_message_saves_history() -> None:
    repository = create_repository()
    user_session = repository.load_or_create("tester", 777)

    repository.add_assistant_message(
        user_id=user_session.user.id,
        request_id="request-id",
        update_id=1001,
        text="Ответ",
    )
    loaded = repository.load_or_create("tester", 777)

    assert len(loaded.history) == 1
    assert loaded.history[0].role == "assistant"
    assert loaded.history[0].telegram_message_id == 0
    assert loaded.history[0].text == "Ответ"


def test_save_dialog_state_updates_state() -> None:
    repository = create_repository()
    user_session = repository.load_or_create("tester", 777)

    repository.save_dialog_state(
        user_session.user.id,
        {
            "project": "obvodny_118",
            "metrics": ["revenue"],
        },
    )
    loaded = repository.load_or_create("tester", 777)

    assert loaded.state == {
        "project": "obvodny_118",
        "metrics": ["revenue"],
    }


def test_save_last_result_creates_and_updates_last_result() -> None:
    repository = create_repository()
    user_session = repository.load_or_create("tester", 777)

    repository.save_last_result(
        user_session.user.id,
        data={"rows": [{"revenue": 100}]},
        query_frame={"metrics": ["revenue"]},
    )
    repository.save_last_result(
        user_session.user.id,
        data={"rows": [{"revenue": 200}]},
        query_frame={"metrics": ["revenue"], "project": "obvodny_118"},
    )
    loaded = repository.load_or_create("tester", 777)
    last_result = repository.db.scalar(
        select(LastResult).where(LastResult.user_id == user_session.user.id),
    )

    assert loaded.last_result == {"rows": [{"revenue": 200}]}
    assert last_result is not None
    assert last_result.query_frame == {"metrics": ["revenue"], "project": "obvodny_118"}


def test_clear_state_resets_state_and_last_result() -> None:
    repository = create_repository()
    user_session = repository.load_or_create("tester", 777)
    dialog_state = repository.db.scalar(
        select(DialogState).where(DialogState.user_id == user_session.user.id),
    )
    assert dialog_state is not None
    dialog_state.data = {"project": "obvodny"}
    repository.db.add(
        LastResult(
            user_id=user_session.user.id,
            data={"value": 100},
            query_frame={"metric": "revenue"},
        ),
    )
    repository.db.commit()

    repository.clear_state(user_session.user.id)
    loaded = repository.load_or_create("tester", 777)

    assert loaded.state == {}
    assert loaded.last_result is None
