from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.repositories import UserSession
from app.llm.dictionary import build_llm_dictionary


SYSTEM_RULES = [
    "Return only valid JSON.",
    "Do not calculate final data values.",
    "Do not invent numbers.",
    "Do not generate SQL.",
    "Use only allowed dictionary values.",
    "Return state_delta or operation for backend execution.",
    "Do not reveal personal data.",
]


class PeriodContext(BaseModel):
    from_date: str | None = Field(default=None, alias="from")
    to: str | None = None
    label: str | None = None


class DialogStateContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    report_type: str | None = None
    project: str | None = None
    period: PeriodContext = Field(default_factory=PeriodContext)
    metrics: list[str] = Field(default_factory=list)
    view: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    group_by: list[str] = Field(default_factory=list)
    sort: str | None = None
    limit: int | None = None
    last_intent: str | None = None
    awaiting_clarification: bool = False
    clarification_target: str | None = None


class HistoryMessage(BaseModel):
    role: str
    text: str | None


class LLMInput(BaseModel):
    user_message: str
    dialog_state: DialogStateContext
    history: list[HistoryMessage]
    last_result_summary: dict[str, Any] | None
    system_rules: list[str]
    dictionary: dict[str, Any]


def build_dialog_state(raw_state: dict[str, Any] | None) -> DialogStateContext:
    return DialogStateContext.model_validate(raw_state or {})


def build_history(user_session: UserSession, history_limit: int) -> list[HistoryMessage]:
    history_items = list(reversed(user_session.history[:history_limit]))
    return [
        HistoryMessage(role=item.role, text=item.text)
        for item in history_items
        if item.text
    ]


def build_last_result_summary(last_result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not last_result:
        return None

    return {
        "metrics": last_result.get("metrics"),
        "project": last_result.get("project"),
        "period": last_result.get("period"),
        "items": last_result.get("items"),
        "raw": last_result if not any(key in last_result for key in {"metrics", "project", "period", "items"}) else None,
    }


def build_llm_input(
    user_message: str | None,
    user_session: UserSession,
    history_limit: int = 20,
) -> LLMInput:
    return LLMInput(
        user_message=user_message or "",
        dialog_state=build_dialog_state(user_session.state),
        history=build_history(user_session, history_limit),
        last_result_summary=build_last_result_summary(user_session.last_result),
        system_rules=SYSTEM_RULES,
        dictionary=build_llm_dictionary(),
    )
