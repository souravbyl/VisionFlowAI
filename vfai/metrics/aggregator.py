import time
from collections import defaultdict, deque
from vfai.metrics.event import MetricEvent


class MetricsAggregator:
    def __init__(self, window_size=100):
        self.data = defaultdict(
            lambda: {
                "in": 0,
                "out": 0,
                "drop": 0,
                "timestamps": deque(maxlen=window_size),
                "proc_lat": deque(maxlen=window_size),
                "queue_wait": deque(maxlen=window_size),
                "total_lat": deque(maxlen=window_size),
            }
        )

    def process_event(self, ev: MetricEvent):
        d = self.data[ev.stage]

        if ev.event == "in":
            d["in"] += 1

        elif ev.event == "drop":
            d["drop"] += 1

        elif ev.event == "out":
            now = ev.t_end if ev.t_end is not None else time.perf_counter()

            d["out"] += 1
            d["timestamps"].append(now)

            if ev.t_start is not None and ev.t_end is not None:
                d["proc_lat"].append(ev.t_end - ev.t_start)

            if ev.t_capture is not None and ev.t_start is not None:
                d["queue_wait"].append(ev.t_start - ev.t_capture)

            if ev.t_capture is not None and ev.t_end is not None:
                d["total_lat"].append(ev.t_end - ev.t_capture)

    def snapshot(self):
        result = {}

        for stage, d in self.data.items():
            ts = d["timestamps"]

            fps = 0.0
            if len(ts) >= 2:
                dt = ts[-1] - ts[0]
                fps = (len(ts) - 1) / dt if dt > 0 else 0.0

            def avg(x):
                return sum(x) / len(x) if x else 0.0

            result[stage] = {
                "in": d["in"],
                "out": d["out"],
                "drop": d["drop"],
                "fps": round(fps, 2),
                "proc_ms": round(avg(d["proc_lat"]) * 1000, 2),
                "queue_ms": round(avg(d["queue_wait"]) * 1000, 2),
                "total_ms": round(avg(d["total_lat"]) * 1000, 2),
            }

        return result
