import httpx


CHAT_ACTION_TYPING = "typing"
CHAT_ACTION_UPLOAD_DOCUMENT = "upload_document"


class TelegramClient:
    def __init__(self, bot_token: str | None, proxy: str | None = None) -> None:
        self.bot_token = bot_token
        self.proxy = proxy

    async def send_message(self, chat_id: int, text: str) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10, proxy=self.proxy) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "text": text},
            )
            response.raise_for_status()

    async def send_document(
        self,
        chat_id: int,
        file_bytes: bytes,
        filename: str,
        caption: str | None = None,
        mime_type: str = "application/pdf",
    ) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        files = {"document": (filename, file_bytes, mime_type)}
        async with httpx.AsyncClient(timeout=30, proxy=self.proxy) as client:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()

    async def send_chat_action(self, chat_id: int, action: str) -> None:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendChatAction"
        async with httpx.AsyncClient(timeout=10, proxy=self.proxy) as client:
            response = await client.post(
                url,
                json={"chat_id": chat_id, "action": action},
            )
            response.raise_for_status()

    async def set_my_commands(self, commands: list[dict[str, str]]) -> dict[str, object]:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/setMyCommands"
        async with httpx.AsyncClient(timeout=10, proxy=self.proxy) as client:
            response = await client.post(url, json={"commands": commands})
            response.raise_for_status()
            return response.json()

    async def delete_webhook(self) -> dict[str, object]:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/deleteWebhook"
        async with httpx.AsyncClient(timeout=10, proxy=self.proxy) as client:
            response = await client.post(url, json={"drop_pending_updates": False})
            response.raise_for_status()
            return response.json()

    async def get_updates(self, offset: int | None = None, timeout: int = 25, limit: int = 20) -> list[dict[str, object]]:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        payload: dict[str, object] = {"timeout": timeout, "limit": limit}
        if offset is not None:
            payload["offset"] = offset
        async with httpx.AsyncClient(timeout=timeout + 10, proxy=self.proxy) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError("Telegram getUpdates returned error")
            result = data.get("result", [])
            return result if isinstance(result, list) else []

    async def get_me(self) -> dict[str, object]:
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        async with httpx.AsyncClient(timeout=10, proxy=self.proxy) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
