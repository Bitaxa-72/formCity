from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSpec:
    unit: str
    group_by: set[str]
    filters: set[str]
    projects: set[str]
    privacy: str = "safe_aggregate"


@dataclass(frozen=True)
class CompatibilityCheck:
    valid: bool
    error: str | None = None
    message: str | None = None
