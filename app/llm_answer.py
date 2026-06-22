import json

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import Settings
from app.response_data import ResponseData


ANSWER_SYSTEM_PROMPT = """
Ты оформляешь проверенные данные backend в короткий русский ответ.
Используй только числа, метрики, таблицы и source из входного JSON.
Не добавляй новые цифры.
Не делай новые расчеты.
Не упоминай SQL, JSON, backend и внутренние этапы.
Верни только валидный JSON.
"""


class LLMAnswerError(RuntimeError):
    pass


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    used_metrics: list[str] = Field(default_factory=list)
    source: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


def build_unready_answer(response_data: ResponseData | None) -> AnswerDraft:
    errors = response_data.errors if response_data else ["response_data_missing"]
    return AnswerDraft(
        text="Не удалось подготовить проверенный ответ по данным.",
        used_metrics=[],
        source=response_data.source if response_data else {},
        warnings=errors,
    )


class OpenAILLMAnswerer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def build_answer(self, response_data: ResponseData | None) -> AnswerDraft:
        if response_data is None or not response_data.ready:
            return build_unready_answer(response_data)
        if not self.settings.openai_key:
            raise LLMAnswerError("OPENAI_KEY is not configured")
        if not self.settings.openai_model:
            raise LLMAnswerError("OPENAI_MODEL is not configured")

        async with httpx.AsyncClient(timeout=30, proxy=self.settings.proxy) as http_client:
            client = AsyncOpenAI(api_key=self.settings.openai_key, http_client=http_client)
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": response_data.model_dump_json()},
                ],
                temperature=0,
            )

        content = response.choices[0].message.content
        if not content:
            raise LLMAnswerError("LLM returned empty answer")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMAnswerError("LLM returned invalid answer JSON") from error

        try:
            return AnswerDraft.model_validate(payload)
        except ValidationError as error:
            raise LLMAnswerError("LLM returned invalid answer schema") from error
