import json
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.config import Settings
from app.llm_dictionary import GroupBy, Intent, Metric, OperationSource, OperationType, Project, ReportType
from app.llm_input import LLMInput


PARSER_SYSTEM_PROMPT = """
Ты разбираешь сообщения пользователя для backend.
Верни только валидный JSON.
Не считай значения.
Не придумывай данные.
Не генерируй SQL.
Используй state_delta только для изменений контекста.
Если пользователь просит расчет по прошлому результату, заполни operation.
"""


class LLMParserError(RuntimeError):
    pass


class PeriodDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_date: str | None = Field(default=None, alias="from")
    to: str | None = None
    label: str | None = None


class StateDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: ReportType | None = None
    project: Project | None = None
    period: PeriodDelta | None = None
    metrics: list[Metric] | None = None
    filters: dict[str, Any] | None = None
    group_by: list[GroupBy] | None = None

    def has_updates(self) -> bool:
        return bool(self.model_dump(exclude_none=True))


class OperationOperand(BaseModel):
    source: OperationSource
    metric: Metric | None = None
    value: int | float | str | None = None

    @model_validator(mode="after")
    def validate_operand(self) -> "OperationOperand":
        if self.source == OperationSource.LITERAL and self.value is None:
            raise ValueError("literal operand requires value")
        if self.source in {OperationSource.LAST_RESULT, OperationSource.DIALOG_STATE} and self.metric is None:
            raise ValueError("state/result operand requires metric")
        return self


class Operation(BaseModel):
    type: OperationType
    left: OperationOperand | None = None
    right: OperationOperand | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> "Operation":
        if self.left is None:
            raise ValueError("operation requires left operand")
        if self.type != OperationType.AVERAGE and self.right is None:
            raise ValueError("operation requires right operand")
        return self


class LLMParsedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    state_delta: StateDelta = Field(default_factory=StateDelta)
    operation: Operation | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_response(self) -> "LLMParsedResponse":
        if self.needs_clarification and not self.clarification_question:
            raise ValueError("clarification_question is required")
        if self.intent == Intent.MATH_ON_LAST_RESULT and self.operation is None:
            raise ValueError("math_on_last_result requires operation")
        if self.intent == Intent.DATA_QUERY and not self.state_delta.has_updates() and not self.needs_clarification:
            raise ValueError("data_query requires state_delta")
        return self


class OpenAILLMParser:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def parse(self, llm_input: LLMInput) -> LLMParsedResponse:
        if not self.settings.openai_key:
            raise LLMParserError("OPENAI_KEY is not configured")
        if not self.settings.openai_model:
            raise LLMParserError("OPENAI_MODEL is not configured")

        async with httpx.AsyncClient(timeout=30, proxy=self.settings.proxy) as http_client:
            client = AsyncOpenAI(api_key=self.settings.openai_key, http_client=http_client)
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": llm_input.model_dump_json(by_alias=True)},
                ],
                temperature=0,
            )

        content = response.choices[0].message.content
        if not content:
            raise LLMParserError("LLM returned empty content")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMParserError("LLM returned invalid JSON") from error

        try:
            return LLMParsedResponse.model_validate(payload)
        except ValidationError as error:
            raise LLMParserError("LLM returned invalid schema") from error
