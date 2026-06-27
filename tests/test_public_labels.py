import re

from app.llm.answer_labels import METRIC_LABELS as ANSWER_METRIC_LABELS
from app.pipeline.response_data import METRIC_LABELS as RESPONSE_METRIC_LABELS
from app.reports.registry import METRIC_CATALOG


INTERNAL_KEY_RE = re.compile(r"^[a-z]+(?:_[a-z0-9]+)+$")


def all_metric_keys() -> list[str]:
    return sorted({metric for metrics in METRIC_CATALOG.values() for metric in metrics})


def test_all_report_metrics_have_public_labels() -> None:
    metrics = all_metric_keys()

    assert [metric for metric in metrics if metric not in RESPONSE_METRIC_LABELS] == []
    assert [metric for metric in metrics if metric not in ANSWER_METRIC_LABELS] == []


def test_public_labels_do_not_expose_backend_keys() -> None:
    for metric in all_metric_keys():
        assert not INTERNAL_KEY_RE.fullmatch(RESPONSE_METRIC_LABELS[metric])
        assert not INTERNAL_KEY_RE.fullmatch(ANSWER_METRIC_LABELS[metric])
