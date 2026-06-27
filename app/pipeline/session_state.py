from types import SimpleNamespace

from fastapi.encoders import jsonable_encoder

from app.pipeline.context_resolver import empty_dialog_state


def user_session_with_state(user_session: object, state: dict[str, object]) -> object:
    return SimpleNamespace(
        user=user_session.user,
        state=state,
        history=user_session.history,
        last_result=user_session.last_result,
    )


def preserve_admin_debug_flag(source_state: dict[str, object] | None, target_state: dict[str, object]) -> dict[str, object]:
    state_to_save = dict(target_state)
    if source_state and source_state.get("admin_debug_enabled") is True:
        state_to_save["admin_debug_enabled"] = True
    return state_to_save


def clear_state_preserving_admin_debug(
    user_session_repository: object,
    user_id: int,
    source_state: dict[str, object] | None,
) -> None:
    user_session_repository.clear_state(user_id)
    if source_state and source_state.get("admin_debug_enabled") is True:
        user_session_repository.save_dialog_state(user_id, {"admin_debug_enabled": True})


def empty_state_preserving_admin_debug(source_state: dict[str, object] | None) -> dict[str, object]:
    return jsonable_encoder(preserve_admin_debug_flag(source_state, empty_dialog_state()))
