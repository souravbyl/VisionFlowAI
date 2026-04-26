from dataclasses import dataclass


@dataclass(slots=True)
class MetricEvent:
    stage: str
    event: str  # "in", "out", "drop"
    t_capture: float | None = None
    t_start: float | None = None
    t_end: float | None = None
