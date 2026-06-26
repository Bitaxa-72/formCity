import argparse
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.db.database import create_database_tables, get_session_factory
from app.db.models import PaymentCalendarFact


DEFAULT_SOURCE = Path("..") / "\u043e\u0440\u0438\u0433\u0438\u043d\u0430\u043b\u044b \u0442\u0430\u0431\u043b\u0438\u0446" / "\u043f\u043b\u0430\u0442\u0435\u0436\u043d\u044b\u0439 \u043a\u0430\u043b\u0435\u043d\u0434\u0430\u0440\u044c" / "\u043e\u043e\u043e \u0432\u0435\u043b\u043b"
DEFAULT_PROJECT = "moskovsky"
MAIN_NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CELL_RE = re.compile(r"([A-Z]+)([0-9]+)")


@dataclass(frozen=True)
class PaymentCalendarRow:
    project: str
    period_month: date
    article: str
    article_kind: str
    article_order: int
    plan_amount: Decimal | None
    fact_amount: Decimal | None
    deviation_amount: Decimal | None
    source_file: str


@dataclass(frozen=True)
class PaymentCalendarLayout:
    period_column: int
    article_column: int
    plan_column: int
    fact_column: int
    deviation_column: int


def column_to_index(column: str) -> int:
    result = 0
    for char in column:
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def excel_serial_to_date(value: str | int | float | Decimal) -> date:
    serial = int(Decimal(str(value)))
    return (datetime(1899, 12, 30) + timedelta(days=serial)).date()


def excel_serial_to_month(value: str | int | float | Decimal) -> date:
    parsed = excel_serial_to_date(value)
    return parsed.replace(day=1)


def parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str):
        prepared = value.strip().replace(" ", "").replace(",", ".")
        if not prepared:
            return None
    else:
        prepared = str(value)
    try:
        return Decimal(prepared)
    except InvalidOperation:
        return None


def normalize_article(value: str) -> str:
    return " ".join(value.strip().lower().replace("ё", "е").split())


def classify_article(article: str) -> str:
    normalized = normalize_article(article)
    if normalized == "итого платежи":
        return "payment_total"
    if normalized.startswith("поступления"):
        return "income_total"
    if normalized == "остаток дс на начало месяца":
        return "balance_start"
    if normalized == "остаток дс на конец месяца":
        return "balance_end"
    return "detail"


def detect_payment_calendar_layout(rows: dict[int, dict[int, str | None]]) -> PaymentCalendarLayout:
    row_2 = rows.get(2, {})
    period_column = next(
        (
            column
            for column in sorted(row_2)
            if column >= 3 and parse_decimal(row_2.get(column)) is not None
        ),
        None,
    )
    if period_column is None:
        raise ValueError("period_month_not_found")

    return PaymentCalendarLayout(
        period_column=period_column,
        article_column=2,
        plan_column=period_column,
        fact_column=period_column + 1,
        deviation_column=period_column + 2,
    )


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall(f"{MAIN_NAMESPACE}si"):
        parts = [node.text or "" for node in item.iter(f"{MAIN_NAMESPACE}t")]
        values.append("".join(parts))
    return values


def read_first_sheet_name(archive: zipfile.ZipFile) -> str:
    names = archive.namelist()
    if "xl/worksheets/sheet1.xml" in names:
        return "xl/worksheets/sheet1.xml"

    worksheet_names = sorted(name for name in names if name.startswith("xl/worksheets/") and name.endswith(".xml"))
    if not worksheet_names:
        raise ValueError("xlsx_sheet_not_found")
    return worksheet_names[0]


def read_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    value_node = cell.find(f"{MAIN_NAMESPACE}v")

    if cell_type == "inlineStr":
        text_parts = [node.text or "" for node in cell.iter(f"{MAIN_NAMESPACE}t")]
        return "".join(text_parts)

    if value_node is None or value_node.text is None:
        return None

    raw_value = value_node.text
    if cell_type == "s":
        return shared_strings[int(raw_value)]
    return raw_value


def read_xlsx_rows(path: Path, worksheet_name: str | None = None) -> dict[int, dict[int, str | None]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        sheet_name = worksheet_name or read_first_sheet_name(archive)
        root = ElementTree.fromstring(archive.read(sheet_name))

    rows: dict[int, dict[int, str | None]] = {}
    for row in root.iter(f"{MAIN_NAMESPACE}row"):
        row_index = int(row.attrib["r"])
        values: dict[int, str | None] = {}
        for cell in row.findall(f"{MAIN_NAMESPACE}c"):
            ref = cell.attrib.get("r")
            if not ref:
                continue
            match = CELL_RE.fullmatch(ref)
            if not match:
                continue
            values[column_to_index(match.group(1))] = read_cell_value(cell, shared_strings)
        rows[row_index] = values
    return rows


def build_payment_calendar_rows(
    rows: dict[int, dict[int, str | None]],
    project: str,
    source_file: str,
) -> list[PaymentCalendarRow]:
    layout = detect_payment_calendar_layout(rows)
    period_value = rows.get(2, {}).get(layout.period_column)
    if period_value is None:
        raise ValueError("period_month_not_found")

    period_month = excel_serial_to_month(period_value)
    result = []
    for row_index in sorted(rows):
        if row_index < 4:
            continue
        row = rows[row_index]
        article = (row.get(layout.article_column) or "").strip()
        if not article:
            continue
        result.append(
            PaymentCalendarRow(
                project=project,
                period_month=period_month,
                article=article,
                article_kind=classify_article(article),
                article_order=row_index,
                plan_amount=parse_decimal(row.get(layout.plan_column)),
                fact_amount=parse_decimal(row.get(layout.fact_column)),
                deviation_amount=parse_decimal(row.get(layout.deviation_column)),
                source_file=source_file,
            ),
        )
    return result


def parse_payment_calendar_file(path: Path, project: str) -> list[PaymentCalendarRow]:
    return build_payment_calendar_rows(
        rows=read_xlsx_rows(path),
        project=project,
        source_file=path.name,
    )


def find_xlsx_files(source: Path) -> list[Path]:
    return sorted(path for path in source.rglob("*.xlsx") if not path.name.startswith("~$"))


def replace_payment_calendar_rows(session: Session, rows: list[PaymentCalendarRow]) -> int:
    periods = {row.period_month for row in rows}
    project = rows[0].project if rows else None

    if project and periods:
        session.execute(
            delete(PaymentCalendarFact).where(
                PaymentCalendarFact.project == project,
                PaymentCalendarFact.period_month.in_(periods),
            ),
        )

    session.add_all(
        PaymentCalendarFact(
            project=row.project,
            period_month=row.period_month,
            article=row.article,
            article_kind=row.article_kind,
            article_order=row.article_order,
            plan_amount=row.plan_amount,
            fact_amount=row.fact_amount,
            deviation_amount=row.deviation_amount,
            source_file=row.source_file,
        )
        for row in rows
    )
    session.commit()
    return len(rows)


def import_payment_calendar(session: Session, source: Path, project: str) -> tuple[int, int]:
    files = find_xlsx_files(source)
    rows = []
    for file_path in files:
        rows.extend(parse_payment_calendar_file(file_path, project))
    return replace_payment_calendar_rows(session, rows), len(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    args = parser.parse_args()

    settings = load_settings()
    create_database_tables(settings.database_url)
    session_factory = get_session_factory(settings.database_url)
    with session_factory() as session:
        row_count, file_count = import_payment_calendar(session, args.source, args.project)

    print(f"Imported {row_count} rows from {file_count} files for project={args.project}")


if __name__ == "__main__":
    main()
