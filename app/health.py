from dataclasses import dataclass

import httpx

from app.config import Settings
from app.telegram_client import TelegramClient


PROXY_ERROR_MESSAGE = "Прокси не работает"
TELEGRAM_ERROR_MESSAGE = "Telegram временно недоступен"
LLM_ERROR_MESSAGE = "Пополните баланс токенов"


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    failed_service: str | None = None
    user_message: str | None = None


class HealthChecker:
    def __init__(self, settings: Settings, telegram_client: TelegramClient) -> None:
        self.settings = settings
        self.telegram_client = telegram_client

    async def check_all(self) -> HealthResult:
        # Proxy нужен только для LLM, Telegram проверяется напрямую.
        if not await self.check_proxy():
            return HealthResult(False, "proxy", PROXY_ERROR_MESSAGE)

        if not await self.check_telegram():
            return HealthResult(False, "telegram", TELEGRAM_ERROR_MESSAGE)

        if not await self.check_llm():
            return HealthResult(False, "llm", LLM_ERROR_MESSAGE)

        return HealthResult(True)

    async def check_proxy(self) -> bool:
        if not self.settings.proxy:
            return False

        try:
            async with httpx.AsyncClient(timeout=10, proxy=self.settings.proxy) as client:
                response = await client.get("https://api.telegram.org")
            return response.status_code < 500
        except Exception:
            return False

    async def check_telegram(self) -> bool:
        try:
            await self.telegram_client.get_me()
            return True
        except Exception:
            return False

    async def check_llm(self) -> bool:
        if not self.settings.openai_key or not self.settings.openai_model:
            return False

        try:
            async with httpx.AsyncClient(timeout=10, proxy=self.settings.proxy) as client:
                response = await client.get(
                    f"https://api.openai.com/v1/models/{self.settings.openai_model}",
                    headers={"Authorization": f"Bearer {self.settings.openai_key}"},
                )
            return response.status_code == 200
        except Exception:
            return False
