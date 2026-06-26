from datetime import date
from pathlib import Path

from app.importers.roadmap import build_roadmap_rows, parse_period_month_from_filename


def test_parse_period_month_from_filename() -> None:
    period = parse_period_month_from_filename(Path("roadmap_30.04.2026.xlsx"))

    assert period == date(2026, 4, 1)


def test_parse_period_month_from_ascii_filename() -> None:
    period = parse_period_month_from_filename(Path("roadmap_2026-04-30.xlsx"))

    assert period == date(2026, 4, 1)


def test_build_roadmap_rows_keeps_safe_steps_and_total() -> None:
    rows = {
        2: {
            2: "number",
            3: "\u0414\u043e\u0440\u043e\u0436\u043d\u0430\u044f \u043a\u0430\u0440\u0442\u0430",
            4: "min",
            5: "max",
        },
        3: {
            2: "1",
            3: "\u0417\u0430\u0441\u0442\u0440\u043e\u0439\u0449\u0438\u043a - \u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430",
            4: "1",
            5: "1",
        },
        4: {
            3: "\u0411\u0410\u041d\u041a - \u0440\u0430\u0441\u0441\u043c\u043e\u0442\u0440\u0435\u043d\u0438\u0435",
            4: "1",
            5: "3",
        },
        5: {
            2: "2",
            3: "\u0420\u041e\u0421\u0420\u0415\u0415\u0421\u0422\u0420 - \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f",
            4: "3",
            5: "7",
        },
        6: {
            3: "\u0418\u0442\u043e\u0433\u043e \u0432 \u0440\u0430\u0431\u043e\u0447\u0438\u0445 \u0434\u043d\u044f\u0445",
            4: "9",
            5: "15",
        },
    }

    result = build_roadmap_rows(rows, "all", date(2026, 4, 1), "roadmap.xlsx")

    assert len(result) == 4
    assert result[0].step_no == 1
    assert result[0].parent_step_no is None
    assert result[0].min_work_days == 1
    assert result[1].step_no is None
    assert result[1].parent_step_no == 1
    assert result[1].is_external is True
    assert result[2].step_no == 2
    assert result[2].is_external is True
    assert result[3].is_total is True
    assert result[3].parent_step_no is None
    assert result[3].min_work_days == 9
    assert result[3].max_work_days == 15
