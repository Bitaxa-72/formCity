START_MESSAGE = (
    "Привет, я бот formcity. Я даю информацию по данным из таблиц.\n\n"
    "Для лучшей точности указывайте какой тип отчета вас интересует, проект и метрику."
    "Доступные типы отчетов: сводная, модель, платежный календарь, "
    "дорожная карта, остатки в продаже, ДЗ и брони, отчет о продажах, "
    "отчет об исполнении плана продаж, отчет по агентам, непроектные расходы.\n\n"
)

INFO_MESSAGE = (
    "Данные берутся из базы проекта.\n\n"
    "Доступные типы отчетов: сводная, модель, платежный календарь, "
    "дорожная карта, остатки в продаже, ДЗ и брони, отчет о продажах, "
    "отчет об исполнении плана продаж, отчет по агентам, непроектные расходы.\n\n"
    "Доступные проекты: Обводный 118, Велл Московский, Евгеньевский."
)

CLEAR_MESSAGE = "Контекст диалога очищен."

COMMAND_RESPONSES = {
    "/start": START_MESSAGE,
    "/info": INFO_MESSAGE,
    "/clear": CLEAR_MESSAGE,
}

def normalize_command(text: str | None) -> str | None:
    if not text:
        return None

    first_token = text.strip().split(maxsplit=1)[0].lower()
    if not first_token.startswith("/"):
        return None

    command = first_token.split("@", 1)[0]
    return command if command in COMMAND_RESPONSES else None
