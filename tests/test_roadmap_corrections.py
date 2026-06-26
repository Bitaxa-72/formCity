from app.reports.roadmap.corrections import resolve_roadmap_recovery


def test_resolve_roadmap_recovery_detects_steps_word() -> None:
    result = resolve_roadmap_recovery("этапы")

    assert result is not None
    assert result[1]["view"] == "roadmap_steps"


def test_resolve_roadmap_recovery_does_not_treat_floor_as_step() -> None:
    result = resolve_roadmap_recovery("сколько этажей?")

    assert result is None
