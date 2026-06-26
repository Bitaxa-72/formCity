import asyncio
import logging

import httpx

from app.bot.telegram_client import TelegramClient
from app.core.config import load_settings
from app.main import app


logger = logging.getLogger("formcity.polling")


async def process_update_through_app(update: dict[str, object]) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://formcity.local", timeout=120) as client:
        response = await client.post("/webhook/telegram", json=update)
        response.raise_for_status()


async def run_polling() -> None:
    settings = load_settings()
    telegram_client = TelegramClient(settings.bot_token, settings.telegram_proxy)

    offset = None
    webhook_deleted = False
    while True:
        try:
            if not webhook_deleted:
                await telegram_client.delete_webhook()
                webhook_deleted = True

            updates = await telegram_client.get_updates(offset=offset)
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                await process_update_through_app(update)
        except Exception as error:
            logger.warning("polling_iteration_failed error=%s", type(error).__name__)
            await asyncio.sleep(5)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
