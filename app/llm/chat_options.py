def build_chat_completion_options(model: str | None) -> dict[str, float]:
    if model and model.startswith("gpt-5"):
        return {}
    return {"temperature": 0}
