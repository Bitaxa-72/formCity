import httpx


class TelegramClient:
    def __init__(self, bot_token: str | None) -> None:
        self.bot_token = bot_token

    async def send_message(self, chat_id: int, text: str) -> None:
        # Реальный запрос нужен только после проверки whitelist.
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": text},
            )
            response.raise_for_status()

    async def get_me(self) -> dict[str, object]:
        # getMe проверяет, что Telegram token живой и API доступен.
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
