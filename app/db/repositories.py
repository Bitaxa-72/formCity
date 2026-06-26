from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access import normalize_username
from app.db.models import DialogState, LastResult, MessageHistory, User


@dataclass(frozen=True)
class UserSession:
    user: User
    state: dict[str, Any]
    history: list[MessageHistory]
    last_result: dict[str, Any] | None


class UserSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load_or_create(self, username: str, chat_id: int) -> UserSession:
        normalized_username = normalize_username(username)
        if not normalized_username:
            raise ValueError("username is required")

        user = self.db.scalar(select(User).where(User.username == normalized_username))
        if user is None:
            user = User(username=normalized_username, telegram_chat_id=chat_id)
            self.db.add(user)
            self.db.flush()
            self.db.add(DialogState(user_id=user.id, data={}))
            self.db.commit()
            self.db.refresh(user)
        elif user.telegram_chat_id != chat_id:
            user.telegram_chat_id = chat_id
            self.db.commit()

        dialog_state = self.db.scalar(select(DialogState).where(DialogState.user_id == user.id))
        if dialog_state is None:
            dialog_state = DialogState(user_id=user.id, data={})
            self.db.add(dialog_state)
            self.db.commit()

        last_result = self.db.scalar(select(LastResult).where(LastResult.user_id == user.id))
        history = list(
            self.db.scalars(
                select(MessageHistory)
                .where(MessageHistory.user_id == user.id)
                .order_by(MessageHistory.created_at.desc(), MessageHistory.id.desc())
                .limit(20),
            ),
        )

        return UserSession(
            user=user,
            state=dialog_state.data or {},
            history=history,
            last_result=last_result.data if last_result else None,
        )

    def add_user_message(
        self,
        user_id: int,
        request_id: str,
        update_id: int,
        telegram_message_id: int,
        text: str | None,
    ) -> None:
        self.db.add(
            MessageHistory(
                user_id=user_id,
                request_id=request_id,
                update_id=update_id,
                telegram_message_id=telegram_message_id,
                role="user",
                text=text,
            ),
        )
        self.db.commit()

    def add_assistant_message(
        self,
        user_id: int,
        request_id: str,
        update_id: int,
        text: str | None,
    ) -> None:
        self.db.add(
            MessageHistory(
                user_id=user_id,
                request_id=request_id,
                update_id=update_id,
                telegram_message_id=0,
                role="assistant",
                text=text,
            ),
        )
        self.db.commit()

    def save_dialog_state(self, user_id: int, data: dict[str, Any]) -> None:
        dialog_state = self.db.scalar(select(DialogState).where(DialogState.user_id == user_id))
        if dialog_state is None:
            self.db.add(DialogState(user_id=user_id, data=data))
        else:
            dialog_state.data = data
        self.db.commit()

    def save_last_result(
        self,
        user_id: int,
        data: dict[str, Any],
        query_frame: dict[str, Any],
    ) -> None:
        last_result = self.db.scalar(select(LastResult).where(LastResult.user_id == user_id))
        if last_result is None:
            self.db.add(
                LastResult(
                    user_id=user_id,
                    data=data,
                    query_frame=query_frame,
                ),
            )
        else:
            last_result.data = data
            last_result.query_frame = query_frame
        self.db.commit()

    def clear_state(self, user_id: int) -> None:
        dialog_state = self.db.scalar(select(DialogState).where(DialogState.user_id == user_id))
        if dialog_state is None:
            self.db.add(DialogState(user_id=user_id, data={}))
        else:
            dialog_state.data = {}

        last_result = self.db.scalar(select(LastResult).where(LastResult.user_id == user_id))
        if last_result is not None:
            self.db.delete(last_result)

        self.db.commit()
