from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    # Telegram может прислать больше полей, чем нужно текущему этапу.
    model_config = ConfigDict(extra="allow")

    id: int
    is_bot: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class TelegramChat(BaseModel):
    # Лишние поля сохраняют совместимость с разными типами чатов.
    model_config = ConfigDict(extra="allow")

    id: int
    type: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None


class TelegramMessage(BaseModel):
    # Схема описывает только поля, нужные webhook на первом этапе.
    model_config = ConfigDict(extra="allow")

    message_id: int
    date: int | None = None
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None


class TelegramUpdate(BaseModel):
    # Update может быть message, edited_message или другим типом события.
    model_config = ConfigDict(extra="allow")

    update_id: int
    message: TelegramMessage | None = None
    edited_message: TelegramMessage | None = None
    callback_query: dict[str, Any] | None = None
