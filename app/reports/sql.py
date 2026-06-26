from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricSQLSpec:
    expression: str
    alias: str


@dataclass(frozen=True)
class ReportSQLTemplate:
    table: str
    date_column: str
    project_column: str
    metrics: dict[str, MetricSQLSpec]
    group_by_columns: dict[str, str]
    filter_columns: dict[str, str]
    dimension_columns: dict[str, str]
    context_metrics: list[str] = field(default_factory=list)
