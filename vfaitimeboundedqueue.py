import time
from queue import Queue
from typing import Optional
from collections import deque

from metrics.event import MetricEvent


class TimeBoundedQueue:
    def __init__(self, metrics_q: Queue, max_age_sec: float, max_size: int = 0):
        self.__metrics_q = metrics_q
        self.max_age = max_age_sec
        self.max_size = max_size
        self.q = deque()

    def _evict_old(self, now: float):
        dropped = 0
        while self.q:
            frame = self.q[0]
            if (now - frame._epoch) > self.max_age:
                self.q.popleft()
                dropped += 1
            else:
                break

        for _ in range(dropped):
            self.__metrics_q.put(
                MetricEvent("queue", "drop", t_end=now)
            )

    def enqueue(self, frame):
        now = time.perf_counter()

        # 1. Remove stale frames
        self._evict_old(now)

        # 2. Optional size cap (drop oldest)
        dropped = 0
        if self.max_size > 0 and len(self.q) >= self.max_size:
            self.q.popleft()
            dropped = 1
        
        if dropped:
            self.__metrics_q.put(MetricEvent("queue", "drop", t_end=time.perf_counter()))

        # 3. Add new frame
        self.q.append(frame)
        self.__metrics_q.put(MetricEvent("queue", "in"))

    def dequeue(self) -> Optional[object]:
        now = time.perf_counter()

        # 1. Clean stale first
        self._evict_old(now)

        if not self.q:
            return None

        item = self.q.popleft()
        self.__metrics_q.put(MetricEvent("queue", "out", t_end=time.perf_counter()))
        return item

    def size(self):
        return len(self.q)
