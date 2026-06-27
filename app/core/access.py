UNAUTHORIZED_ACCESS_MESSAGE = (
    "Доброго времени суток! \n"
    "У вас нет доступа к работе с данными, обратитесь к руководителю проекта для получения доступа"
)


def normalize_username(username: str | None) -> str | None:
    if username is None:
        return None

    normalized = username.strip().lstrip("@").lower()
    return normalized or None


def is_username_allowed(username: str | None, allowed_usernames: set[str]) -> bool:
    normalized = normalize_username(username)
    return normalized in allowed_usernames if normalized else False
