import json
from typing import Any, Literal

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.config import Settings
from app.llm.chat_options import build_chat_completion_options
from app.llm.dictionary import (
    Dimension,
    GroupBy,
    Intent,
    Metric,
    OperationSource,
    OperationType,
    PaymentCalendarView,
    Project,
    ReportType,
)
from app.llm.input import LLMInput


from app.llm.parser_prompt import PARSER_SYSTEM_PROMPT, REPAIR_SYSTEM_PROMPT


class LLMParserError(RuntimeError):
    pass


class PeriodDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mode: Literal["all"] | None = None
    from_date: str | None = Field(default=None, alias="from")
    to: str | None = None
    label: str | None = None


class StateDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: ReportType | None = None
    project: Project | None = None
    period: PeriodDelta | None = None
    metrics: list[Metric] | None = None
    view: PaymentCalendarView | None = None
    dimension: Dimension | None = None
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
        if self.intent in {Intent.DATA_QUERY, Intent.DIMENSION_QUERY} and not self.state_delta.has_updates() and not self.needs_clarification:
            raise ValueError("data/dimension query requires state_delta")
        return self


def has_concrete_period(period: dict[str, Any]) -> bool:
    label = str(period.get("label") or "").strip().lower()
    if period.get("from") or period.get("to"):
        return True
    if label and label not in {"весь период", "весь доступный период", "all", "whole period"}:
        return True
    return False


def normalize_llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    state_delta = normalized.get("state_delta")

    if isinstance(state_delta, dict) and state_delta:
        intent = normalized.get("intent")
        if intent in {"generate_report", "report", "query", "get_data", "get_report"}:
            normalized["intent"] = Intent.DIMENSION_QUERY.value if state_delta.get("dimension") and not state_delta.get("metrics") else Intent.DATA_QUERY.value

    if "intent" not in normalized and isinstance(state_delta, dict) and state_delta:
        if state_delta.get("dimension") and not state_delta.get("metrics"):
            normalized["intent"] = Intent.DIMENSION_QUERY.value
        else:
            normalized["intent"] = Intent.DATA_QUERY.value

    if isinstance(state_delta, dict) and isinstance(state_delta.get("period"), dict):
        period = dict(state_delta["period"])
        if period.get("mode") == "all" and has_concrete_period(period):
            period.pop("mode", None)
            state_delta = dict(state_delta)
            state_delta["period"] = period
            normalized["state_delta"] = state_delta

    return normalized


def format_validation_errors(error: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": list(item.get("loc", [])),
            "type": item.get("type"),
            "msg": item.get("msg"),
        }
        for item in error.errors()
    ]


def build_repair_payload(invalid_payload: Any, error: Exception) -> str:
    if isinstance(error, ValidationError):
        errors: Any = format_validation_errors(error)
    elif isinstance(error, json.JSONDecodeError):
        errors = [
            {
                "loc": [],
                "type": "json_decode_error",
                "msg": str(error),
            },
        ]
    else:
        errors = [
            {
                "loc": [],
                "type": type(error).__name__,
                "msg": str(error),
            },
        ]

    return json.dumps(
        {
            "invalid_json": invalid_payload,
            "validation_errors": errors,
            "repair_rules": [
                "Return one JSON object only.",
                "Keep the same semantic meaning.",
                "Add missing required technical fields when obvious.",
                "Remove unknown fields.",
                "Use only allowed dictionary enum values.",
            ],
            "schema_shape": {
                "intent": "required enum",
                "state_delta": "object",
                "operation": "object or null",
                "needs_clarification": "boolean",
                "clarification_question": "string or null",
                "confidence": "number from 0 to 1",
            },
        },
        ensure_ascii=False,
    )


class OpenAILLMParser:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def request_json(self, client: AsyncOpenAI, messages: list[dict[str, str]]) -> str:
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            response_format={"type": "json_object"},
            messages=messages,
            **build_chat_completion_options(self.settings.openai_model),
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMParserError("LLM returned empty content")
        return content

    def validate_payload(self, payload: dict[str, Any]) -> LLMParsedResponse:
        return LLMParsedResponse.model_validate(normalize_llm_payload(payload))

    async def repair_payload(
        self,
        client: AsyncOpenAI,
        invalid_payload: Any,
        error: Exception,
    ) -> dict[str, Any]:
        content = await self.request_json(
            client,
            [
                {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": build_repair_payload(invalid_payload, error)},
            ],
        )
        try:
            repaired_payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMParserError("LLM repair returned invalid JSON") from error
        if not isinstance(repaired_payload, dict):
            raise LLMParserError("LLM repair returned non-object JSON")
        return repaired_payload

    async def parse(self, llm_input: LLMInput) -> LLMParsedResponse:
        if not self.settings.openai_key:
            raise LLMParserError("OPENAI_KEY is not configured")
        if not self.settings.openai_model:
            raise LLMParserError("OPENAI_MODEL is not configured")

        async with httpx.AsyncClient(timeout=30, proxy=self.settings.proxy) as http_client:
            client = AsyncOpenAI(api_key=self.settings.openai_key, http_client=http_client)
            content = await self.request_json(
                client,
                [
                    {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": llm_input.model_dump_json(by_alias=True)},
                ],
            )

            try:
                payload = json.loads(content)
            except json.JSONDecodeError as error:
                repaired_payload = await self.repair_payload(client, content, error)
                try:
                    return self.validate_payload(repaired_payload)
                except ValidationError as repair_error:
                    raise LLMParserError("LLM repair returned invalid schema") from repair_error

            if not isinstance(payload, dict):
                repaired_payload = await self.repair_payload(
                    client,
                    payload,
                    ValueError("LLM returned non-object JSON"),
                )
                try:
                    return self.validate_payload(repaired_payload)
                except ValidationError as repair_error:
                    raise LLMParserError("LLM repair returned invalid schema") from repair_error

            try:
                return self.validate_payload(payload)
            except ValidationError as error:
                repaired_payload = await self.repair_payload(client, payload, error)
                try:
                    return self.validate_payload(repaired_payload)
                except ValidationError as repair_error:
                    raise LLMParserError("LLM repair returned invalid schema") from repair_error
