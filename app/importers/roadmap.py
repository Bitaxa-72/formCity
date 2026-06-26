import argparse
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.db.database import create_database_tables, get_session_factory
from app.db.models import RoadmapStep
from app.importers.payment_calendar import read_xlsx_rows


DEFAULT_SOURCE = Path("..") / "\u043e\u0440\u0438\u0433\u0438\u043d\u0430\u043b\u044b \u0442\u0430\u0431\u043b\u0438\u0446" / "\u0434\u043e\u0440\u043e\u0436\u043d\u0430\u044f \u043a\u0430\u0440\u0442\u0430"
DEFAULT_PROJECT = "all"
SAFE_ROADMAP_SHEET = "xl/worksheets/sheet2.xml"
SOURCE_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
ASCII_SOURCE_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass(frozen=True)
class RoadmapRow:
    project: str
    period_month: date
    row_order: int
    step_no: int | None
    parent_step_no: int | None
    action_text: str
    min_work_days: int | None
    max_work_days: int | None
    is_external: bool
    is_total: bool
    source_file: str


def parse_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        prepared = value.strip().replace(" ", "")
        if not prepared:
            return None
    else:
        prepared = str(value)
    try:
        return int(Decimal(prepared))
    except (InvalidOperation, ValueError):
        return None


def parse_period_month_from_filename(path: Path) -> date:
    match = SOURCE_DATE_RE.search(path.name)
    if match:
        month = int(match.group(2))
        year = int(match.group(3))
        return date(year, month, 1)

    match = ASCII_SOURCE_DATE_RE.search(path.name)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        return date(year, month, 1)

    raise ValueError("roadmap_period_not_found")


def is_external_action(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized.startswith("банк") or normalized.startswith("росреестр")


def is_total_row(text: str) -> bool:
    return text.strip().lower().startswith("итого")


def build_roadmap_rows(
    rows: dict[int, dict[int, str | None]],
    project: str,
    period_month: date,
    source_file: str,
) -> list[RoadmapRow]:
    result = []
    parent_step_no: int | None = None

    for row_index in sorted(rows):
        row = rows[row_index]
        action_text = (row.get(3) or "").strip()
        if not action_text:
            continue
        if row_index < 2 or action_text.startswith("Дорожная карта"):
            continue

        step_no = parse_int(row.get(2))
        total = is_total_row(action_text)
        if step_no is not None:
            parent_step_no = step_no

        result.append(
            RoadmapRow(
                project=project,
                period_month=period_month,
                row_order=row_index,
                step_no=step_no,
                parent_step_no=None if step_no is not None or total else parent_step_no,
                action_text=action_text,
                min_work_days=parse_int(row.get(4)),
                max_work_days=parse_int(row.get(5)),
                is_external=is_external_action(action_text),
                is_total=total,
                source_file=source_file,
            ),
        )
    return result


def parse_roadmap_file(path: Path, project: str) -> list[RoadmapRow]:
    return build_roadmap_rows(
        rows=read_xlsx_rows(path, SAFE_ROADMAP_SHEET),
        project=project,
        period_month=parse_period_month_from_filename(path),
        source_file=path.name,
    )


def find_xlsx_files(source: Path) -> list[Path]:
    return sorted(path for path in source.rglob("*.xlsx") if not path.name.startswith("~$"))


def replace_roadmap_rows(session: Session, rows: list[RoadmapRow]) -> int:
    periods = {row.period_month for row in rows}
    project = rows[0].project if rows else None

    if project and periods:
        session.execute(
            delete(RoadmapStep).where(
                RoadmapStep.project == project,
                RoadmapStep.period_month.in_(periods),
            ),
        )

    session.add_all(
        RoadmapStep(
            project=row.project,
            period_month=row.period_month,
            row_order=row.row_order,
            step_no=row.step_no,
            parent_step_no=row.parent_step_no,
            action_text=row.action_text,
            min_work_days=row.min_work_days,
            max_work_days=row.max_work_days,
            is_external=row.is_external,
            is_total=row.is_total,
            source_file=row.source_file,
        )
        for row in rows
    )
    session.commit()
    return len(rows)


def import_roadmap(session: Session, source: Path, project: str) -> tuple[int, int]:
    files = find_xlsx_files(source)
    rows = []
    for file_path in files:
        rows.extend(parse_roadmap_file(file_path, project))
    return replace_roadmap_rows(session, rows), len(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    args = parser.parse_args()

    settings = load_settings()
    create_database_tables(settings.database_url)
    session_factory = get_session_factory(settings.database_url)
    with session_factory() as session:
        row_count, file_count = import_roadmap(session, args.source, args.project)

    print(f"Imported {row_count} rows from {file_count} files for project={args.project}")


if __name__ == "__main__":
    main()
