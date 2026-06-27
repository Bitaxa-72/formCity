from time import perf_counter


def record_timing(timings: dict[str, int], stage: str, started_at: float) -> None:
    timings[f"{stage}_ms"] = int((perf_counter() - started_at) * 1000)
