import logging
import threading
import time
from queue import Queue

import cv2

from vfai.metrics.event import MetricEvent
from vfai.framebuffer import FrameBuffer
from vfai.timeboundedqueue import TimeBoundedQueue
from vfai.config import Config
from vfai.frame import Frame
from vfai.cqueue import CQueue


class Source:
    def __init__(
        self,
        config: Config,
        metrics_q: Queue,
        stop_event: threading.Event,
        qsize: int = 10,
    ):
        # class internals
        self.__name: str = "Worker-VFAISource"

        # thread/event related
        self.__thread = None
        self.__stop_event = stop_event

        # source queue
        self.__frame_queue = CQueue(qsize)
        # self.__frame_queue = FrameBuffer()
        # self.__frame_queue = TimeBoundedQueue(
        #     metrics_q=metrics_q,
        #     max_age_sec=10,#self.__config.queue.max_age_sec,   # e.g. 1–2 sec
        #     max_size=100#self.__config.queue.max_size          # optional (e.g. 50)
        # )

        # metrics queue
        self.__metrics_q = metrics_q

        # general config object
        self.__config = config

        # opencv video capture obj
        self.__cap: cv2.VideoCapture | None = None

        self.__logger = logging.getLogger(__name__)

        self.__frame_count = 0

    def start(self):
        if self.__thread and self.__thread.is_alive():
            return
        self.__thread = threading.Thread(target=self.__run, name=self.__name)
        self.__thread.start()

    def join(self):
        if self.__thread:
            self.__thread.join()

    # def get_frame(self, last_version):
    def get_frame(self):
        try:
            # return self.__frame_queue.read(last_version)
            frame = self.__frame_queue.dequeue()
            # if (
            #     self.__config.debug and frame is not None
            # ):  # and self.__frame_count - frame > 1000:
            #     self.__logger.debug(
            #         f"Dequeued frame ID{frame._id}. Framecount {self.__frame_count}; "
            #         f"Diff {self.__frame_count - frame._id}."
            #     )
            return frame
        finally:
            pass

    def __run(self):
        try:
            self.__run_impl()
        finally:
            # self.__stop()
            self.__cleanup()

    def __stop(self):
        if not self.__stop_event.is_set():
            self.__stop_event.set()

    def __cleanup(self):
        self.__deinit_source()

    def __deinit_source(self):
        if self.__cap is not None:
            self.__cap.release()
            self.__logger.warning("Source released.")
            self.__cap = None

    def __run_impl(self):
        self.__init_source()
        try:
            start = time.perf_counter()
            if self.__config.debug:
                self.__logger.debug(f"Starting grabbing at {time.perf_counter()}")
            while not self.__stop_event.is_set():
                if self.__cap is None:
                    raise ValueError("Capture object is None")
                try:
                    t_capture = time.perf_counter()
                    self.__metrics_q.put(MetricEvent("grabber", "in"))
                    ret, frame = self.__cap.read()
                    if not ret:
                        if self.__config.reconnect_source_on_failure:
                            self.__deinit_source()
                            self.__logger.info(f"Will reconnect source.")
                            self.__init_source()
                            continue
                        else:
                            self.__logger.error(f"Will not reconnect source.")
                            break
                    vframe = Frame(
                        id=self.__frame_count,
                        data=frame,
                        since_start=t_capture - start,
                        epoch=t_capture,
                    )
                    if self.__config.target.width > 0 and self.__config.target.height > 0:
                        frame = cv2.resize(
                            frame, (self.__config.target.width, self.__config.target.height)
                        )
                    self.__frame_count += 1
                    if self.__frame_count % 2 == 0 or self.__frame_count % 3 == 0:
                        self.__metrics_q.put(MetricEvent("grabber", "drop", t_end=time.perf_counter()))
                    else:
                        # self.__frame_queue.write(vframe)
                        self.__frame_queue.enqueue(vframe)
                        # if self.__config.debug and self.__frame_count % 1000 == 0:
                        #     self.__logger.debug(f"Enqueued {self.__frame_count} frames.")
                        self.__metrics_q.put(
                            MetricEvent("grabber", "out", t_end=time.perf_counter())
                        )
                finally:
                    pass
        finally:
            if self.__config.debug:
                self.__logger.debug(f"Deinitialize source at {time.perf_counter()}")
            self.__deinit_source()

    def __init_source(self):
        self.__logger.info("Initializing source...")
        self.__cap = cv2.VideoCapture(self.__config.source.url)

        if self.__cap is None:
            raise ValueError("Could not initialize source!")

        # after init, set values to source
        self.__config.source.width = int(self.__cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.__config.source.height = int(self.__cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.__cap.get(cv2.CAP_PROP_FPS)
        self.__config.source.fps = int(round(fps)) if fps > 0 else 25  # fallback
        self.__config.source.aspect_ratio = (
            self.__config.source.width / self.__config.source.height
        )
        self.__logger.info(
            f"Source frame dimensions: {self.__config.source.width:.0f} x {self.__config.source.height:.0f}, "
            f"Aspect ratio: {self.__config.source.aspect_ratio:.0f}, FPS: {self.__config.source.fps:.0f}"
        )

        if self.__config.target.width > 0 and self.__config.target.height > 0:
            scale = min(
                self.__config.target.width / self.__config.source.width,
                self.__config.target.height / self.__config.source.height,
            )
            self.__config.target.width = int(self.__config.source.width * scale)
            self.__config.target.height = int(self.__config.source.height * scale)
            self.__logger.info(
                f"New frame dimensions: {self.__config.target.width} x {self.__config.target.height}"
            )
        else:
            self.__logger.info(
                f"No target frame dimensions set. Using source dimensions. {self.__config.source.width} x {self.__config.source.height}"
            )

        # if there is no specific ROI saved; use the full frame
        if not self.__config.roi.is_set():
            if self.__config.target.width > 0 and self.__config.target.height > 0:
                self.__config.roi = (
                    0,
                    0,
                    self.__config.target.width,
                    self.__config.target.height,
                )
                self.__logger.info(
                    f"ROI Set to target dimensions: (0, 0) to ({self.__config.target.width}, {self.__config.target.height})"
                )
            else:
                self.__config.roi = (
                    0,
                    0,
                    self.__config.source.width,
                    self.__config.source.height,
                )
                self.__logger.info(
                    f"ROI Set to source dimensions: (0, 0) to ({self.__config.source.width}, {self.__config.source.height})"
                )
        else:
            x1, y1 = self.__config.roi.top_left.xy
            x2, y2 = self.__config.roi.bottom_right.xy
            self.__logger.info(f"ROI already set to: f({x1}, {y1}), ({x2}, {y2})")
