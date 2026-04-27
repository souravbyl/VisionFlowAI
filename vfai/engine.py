import logging
import threading
import time
from queue import Queue

import cv2
import numpy as np

from vfai.cv_util import CV_Show
from vfai.metrics.event import MetricEvent
from vfai.colorcode import COLOR_MOTION, COLOR_TRACK, COLOR_DETECT
from vfai.config import Config
from vfai.detector import Detector
from vfai.event_dispatcher import EventDispatcher
from vfai.motion import Motion
from vfai.source import Source
from vfai.tracker import Tracker


class Engine:
    def __init__(
        self, config: Config, metrics_q: Queue, stop_event: threading.Event
    ):
        self.__name = "Worker-VFAIEngine"
        self.__stop_event = stop_event
        self.__thread = None
        self.__config = config
        self.__metrics_q = metrics_q
        self.__source = Source(
            config=self.__config,
            stop_event=stop_event,
            metrics_q=metrics_q,
            qsize=360000,
        )
        self.__detector = Detector(config=self.__config)
        self.__motion = Motion(config=self.__config)
        self.__event_dispatcher = EventDispatcher(
            self.__config, stop_event=stop_event
        )
        self.__logger = logging.getLogger(__name__)

    def start(self):
        if self.__thread and self.__thread.is_alive():
            return
        self.__thread = threading.Thread(target=self.__run, name=self.__name)
        self.__thread.start()

    def join(self):
        if self.__thread:
            self.__thread.join()
        self.__event_dispatcher.join()
        self.__source.join()

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
        if self.__config.debug:
            cv2.destroyAllWindows()
            self.__logger.info("Destroyed")

    def __run_impl(self):
        self.__source.start()

        # warmup the engine only after receiving the first frame
        warmup_complete = False
        while (not self.__stop_event.is_set()) and (not warmup_complete):
            frame = self.__source.get_frame()
            if frame is None:
                time.sleep(0.001)
                continue
            t_start = time.perf_counter()
            self.__metrics_q.put(MetricEvent("engine", "in"))
            self.__detector.warmup()
            warmup_complete = True
            self.__metrics_q.put(
                MetricEvent(
                    stage="engine",
                    event="out",
                    t_capture=frame._epoch,
                    t_start=t_start,
                    t_end=time.perf_counter(),
                )
            )

        self.__event_dispatcher.start()

        # last_version = 0

        detection_id = 0

        tracker = None
        tracking = False
        last_detect_frame = 0
        redirect_interval = self.__config.source.fps * 5  # after 5 seconds

        while not self.__stop_event.is_set():

            if self.__config.debug:
                # self.__logger.debug(psutil.virtual_memory())

                if cv2.waitKey(1) == ord("q"):
                    pass

            frame = self.__source.get_frame()
            # frame, last_version = self.__source.get_frame(last_version)
            if frame is None:
                time.sleep(0.001)
                continue

            t_start = time.perf_counter()
            try:
                self.__metrics_q.put(MetricEvent("engine", "in"))

                # extract the region we are interested in
                roi_x1, roi_y1 = self.__config.roi.top_left.xy
                roi_x2, roi_y2 = self.__config.roi.bottom_right.xy

                x, y, w, h = roi_x1, roi_y1, (roi_x2 - roi_x1), (roi_y2 - roi_y1)
                roiframe = frame._data[y : y + h, x : x + w]

                if self.__config.imshow_source_frames:
                    CV_Show("Source", roiframe)

                # update last_get_frame_success_time
                # last_get_frame_success_time = t_start

                motion_detected = False
                motion_startT, motion_endT = 0, 0
                motion_x, motion_y, motion_x1, motion_y1 = 0, 0, 0, 0
                motion_roi = None
                try:
                    motion_startT = t_start
                    grayscale = self.__motion.get_grayscale(roiframe)
                    motion_detected, bbox = self.__motion.check_if_motion(
                        grayscale, w, h
                    )
                    motion_endT = time.perf_counter()

                    if motion_detected == False:
                        if self.__config.debug:
                            # self.__logger.debug("Motion not detected")
                            pass
                        continue
                    if bbox is None:
                        if self.__config.debug:
                            # self.__logger.debug("Motion detected, but bbos not found.")
                            pass
                        continue

                    motion_x, motion_y, motion_w, motion_h = bbox
                    motion_x1, motion_y1 = motion_x + motion_w, motion_y + motion_h
                    motion_roi = roiframe[motion_y:motion_y1, motion_x:motion_x1]
                finally:
                    if self.__config.debug:
                        if motion_detected:
                            self.__logger.debug(
                                f"Motion detected at ({motion_x}, {motion_y}), ({motion_x1}, {motion_y1}), "
                                f"Motion Detection Time {(motion_endT - motion_startT):.2f}s"
                            )
                            cv2.rectangle(
                                roiframe,
                                (motion_x, motion_y),
                                (motion_x1, motion_y1),
                                COLOR_MOTION,
                                2,
                            )
                            cv2.putText(
                                roiframe,
                                f"Motion",
                                (motion_x, motion_y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                COLOR_MOTION,
                                2,
                            )
                            if self.__config.imshow_motion_results:
                                if motion_roi is not None:
                                    # CV_Show("Motion(Cropped)", motion_roi)
                                    pass
                                CV_Show("Motion(Full Frame)", roiframe)
                        else:
                            self.__logger.debug("Motion not detected")
                            if self.__config.imshow_motion_results:
                                CV_Show("Motion(Full Frame)", roiframe)

                # =========================================================
                # TRACKING MODE
                # =========================================================
                ok, trackerbbox = False, None
                try:
                    if (
                        self.__config.enable_tracker
                        and tracking
                        and tracker is not None
                    ):
                        ok, trackerbbox = tracker.update(motion_roi)
                        if ok:
                            if frame._id - last_detect_frame > redirect_interval:
                                self.__logger.debug("tracker left for redirection reason")
                                tracking = False
                                tracker = None
                            else:
                                if self.__config.debug:
                                    self.__logger.debug("tracking..")
                                pass
                            pass
                        else:
                            if self.__config.debug:
                                self.__logger.debug("tracker left as new object")
                            tracking = False
                            tracker = None
                finally:
                    if self.__config.debug:
                        if ok and trackerbbox is not None:
                            x, y, w, h = map(int, trackerbbox)
                            cv2.rectangle(
                                roiframe, (x, y), (x + w, y + h), COLOR_TRACK, 2
                            )
                            cv2.putText(
                                roiframe,
                                f"Tracking",
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                COLOR_TRACK,
                                2,
                            )
                        if self.__config.imshow_tracker_results:
                            CV_Show("Tracking", roiframe)

                # perform object detection
                object_detected = False
                try:
                    if not tracking and motion_roi:

                        if self.__config.debug:
                            self.__logger.debug("Calling detector")

                        detection_startT = time.perf_counter()
                        results = self.__detector.detect(frame=motion_roi)
                        detection_endT = time.perf_counter()

                        if self.__config.debug:
                            self.__logger.debug("Response from detector")

                        nowt = time.perf_counter()
                        elapsed = nowt - frame._epoch

                        if self.__config.debug:
                            self.__logger.info(
                                f"captured at {frame._epoch:.0f}, detected at {nowt:.0f} "
                                f"Diff {elapsed:.0f}s, "
                                f"Inference Time {(detection_endT - detection_startT):.2f}s, "
                                f"Source FPS: {self.__config.source.fps}, "
                            )

                        if results is None:
                            continue

                        results = list(results)
                        for r in results:
                            boxes = r.boxes.xyxy.cpu().numpy()
                            scores = r.boxes.conf.cpu().numpy()
                            class_ids = r.boxes.cls.cpu().numpy().astype(int)

                            if len(boxes) == 0:
                                continue

                            # pick best detection
                            i = np.argmax(scores)

                            dx1, dy1, dx2, dy2 = boxes[i]
                            dx1, dy1, dx2, dy2 = int(dx1), int(dy1), int(dx2), int(dy2)

                            # -------- INIT TRACKER --------
                            tracker = Tracker(self.__config, description=f"tracker_{frame._id}")
                            tracker.init(motion_roi, (dx1, dy1, int(dx2 - dx1), int(dy2 - dy1)))
                            tracking = True
                            last_detect_frame = frame._id
                            if self.__config.debug:
                                self.__logger.debug(f"Tracker {frame._id} started.")

                            # map to roiframe
                            dx1_full = int(motion_x + dx1)
                            dy1_full = int(motion_y + dy1)
                            dx2_full = int(motion_x + dx2)
                            dy2_full = int(motion_y + dy2)

                            confidence = float(scores[i])
                            class_id = int(class_ids[i])
                            class_name = self.__detector.get_class_name(class_id)

                            snap = cv2.rectangle(
                                roiframe,
                                (dx1_full, dy1_full),
                                (dx2_full, dy2_full),
                                COLOR_DETECT,
                                2,
                            )
                            self.__event_dispatcher.dispatch_event(
                                frame=frame,
                                detection_id=detection_id,
                                class_id=class_id,
                                class_name=class_name,
                                confidence=confidence,
                                eventtime=nowt,
                                snap=snap,
                                bbox=(dx1_full, dy1_full, dx2_full, dy2_full),
                            )
                            object_detected = True
                            detection_id += 1

                finally:
                    if self.__config.debug:
                        if object_detected:
                            cv2.putText(
                                roiframe,
                                f"{class_name} {confidence:.2f}",
                                (dx1_full, dy1_full - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                COLOR_DETECT,
                                2,
                            )
                        if self.__config.imshow_detection_results:
                            CV_Show("Detection(Full)", roiframe)

            finally:
                self.__metrics_q.put(
                    MetricEvent(
                        stage="engine",
                        event="out",
                        t_capture=frame._epoch,
                        t_start=t_start,
                        t_end=time.perf_counter(),
                    )
                )
