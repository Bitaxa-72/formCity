from dataclasses import dataclass, field

from app.metric_catalog import METRIC_CATALOG, MetricSpec
from app.query_frame import QueryFrame


@dataclass(frozen=True)
class ResolvedMetric:
    name: str
    unit: str
    privacy: str


@dataclass(frozen=True)
class MetricResolution:
    valid: bool
    metrics: list[ResolvedMetric] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    clarification_question: str | None = None


def build_metric_error_question(errors: list[str]) -> str | None:
    if not errors:
        return None
    if "unknown_report_type" in errors:
        return "Уточните тип отчета."
    if "metric_not_allowed_for_report_type" in errors:
        return "Уточните метрику или тип отчета."
    if "group_by_not_allowed_for_metric" in errors:
        return "Уточните группировку для выбранной метрики."
    if "filter_not_allowed_for_metric" in errors:
        return "Уточните фильтры для выбранной метрики."
    if "project_not_allowed_for_metric" in errors:
        return "Уточните проект для выбранной метрики."
    return "Уточните параметры запроса."


def collect_metric_specs(frame: QueryFrame) -> tuple[list[tuple[str, MetricSpec]], list[str]]:
    errors = []
    report_metrics = METRIC_CATALOG.get(frame.report_type or "")
    if report_metrics is None:
        return [], ["unknown_report_type"]

    specs = []
    for metric in frame.metrics:
        spec = report_metrics.get(metric)
        if spec is None:
            errors.append("metric_not_allowed_for_report_type")
            continue
        specs.append((metric, spec))

    return specs, errors


def resolve_metrics(frame: QueryFrame) -> MetricResolution:
    if not frame.ready:
        return MetricResolution(
            valid=False,
            errors=["query_frame_not_ready"],
            clarification_question=frame.clarification_question,
        )

    if frame.operation:
        return MetricResolution(valid=True)

    specs, errors = collect_metric_specs(frame)

    for metric, spec in specs:
        if frame.project and frame.project not in spec.projects:
            errors.append("project_not_allowed_for_metric")

        disallowed_group_by = set(frame.group_by) - spec.group_by
        if disallowed_group_by:
            errors.append("group_by_not_allowed_for_metric")

        disallowed_filters = set(frame.filters) - spec.filters
        if disallowed_filters:
            errors.append("filter_not_allowed_for_metric")

    resolved_metrics = [
        ResolvedMetric(name=metric, unit=spec.unit, privacy=spec.privacy)
        for metric, spec in specs
    ]
    unique_errors = list(dict.fromkeys(errors))

    return MetricResolution(
        valid=not unique_errors,
        metrics=resolved_metrics if not unique_errors else [],
        errors=unique_errors,
        clarification_question=build_metric_error_question(unique_errors),
    )
