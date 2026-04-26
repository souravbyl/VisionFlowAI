import json
import logging
import os
import threading
import time

import cv2

from vfai.config import Config
from vfai.cqueue import CQueue


class EventDispatcher:
    def __init__(
        self,
        config: Config,
        stop_event: threading.Event,
        qsize: int = 10,
        name: str = "EventDispatcher",
    ) -> None:
        # class internals
        self.__name: str = name

        # config
        self.__config = config

        # thread/event related
        self.__thread = None
        self.__stop_event = stop_event

        # event queue
        self.__event_queue = CQueue(qsize)

        self.__logger = logging.getLogger(f"{__name__}")

        # create directory if not exist
        if self.__config.event_dump_path:
            os.makedirs(self.__config.event_dump_path, exist_ok=True)

    def dispatch_event(
        self,
        frame,
        detection_id,
        class_id,
        class_name,
        confidence,
        eventtime,
        snap,
        bbox,
    ):
        event = {
            "id": detection_id,
            "class_name": class_name,
            "class_id": class_id,
            "confidence": f"{confidence:.2f}",
            "since_start": f"{frame._since_start:.2f}",
            "epoch": f"{frame._epoch:.0f}",
            "detected_at": f"{eventtime:.0f}",
            "input_frame_id": f"{frame._id}",
            "snap": snap,
        }
        self.__event_queue.enqueue(event)

    def start(self):
        if self.__thread and self.__thread.is_alive():
            return
        self.__thread = threading.Thread(target=self.__run, name=self.__name)
        self.__thread.start()

    def join(self):
        if self.__thread:
            self.__thread.join()

    def __run(self):
        try:
            self.__run_impl()
        finally:
            self.__stop()
            self.__cleanup()

    def __stop(self):
        if not self.__stop_event.is_set():
            self.__stop_event.set()

    def __cleanup(self):
        pass

    def __run_impl(self):
        start = time.perf_counter()
        if self.__config.debug:
            self.__logger.debug(f"Dispatcher thread started at {start}")
        try:
            while not self.__stop_event.is_set():
                event = self.__event_queue.dequeue()
                if event is None:
                    continue

                snap = event["snap"]
                event.pop("snap", None)
                event_str = json.dumps(event)
                self.__logger.info(event_str)

                # Dump image and json
                event_snap_file = f"F{event['input_frame_id']}-D{event['id']}_C{event['class_name']}-P{event['confidence']}"
                if self.__config.event_dump_path:
                    event_snap_file = (
                        f"{self.__config.event_dump_path}/{event_snap_file}"
                    )
                cv2.imwrite(f"{event_snap_file}.jpg", snap)
                with open(f"{event_snap_file}.json", "w") as f:
                    json.dump(event, f)
                    if self.__config.debug:
                        self.__logger.info(f"Detection saved in {event_snap_file}.json")
        finally:
            if self.__config.debug:
                self.__logger.debug(f"Dispatcher thread ended at {time.perf_counter()}")
