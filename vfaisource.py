import cv2
import time
import logging
import threading
from vfaiqueue import VFAIQueue
from vfaiframe import VFAIFrame
from vfaiconfig import VFAIConfig

class VFAISource:
    def __init__(self, config: VFAIConfig, qsize: int=10, name: str="Worker-VFAISource"):
        # class internals
        self.__name: str = name

        # thread/event related
        self.__thread = None
        self.__stop_event = threading.Event()
        self.__stop_called = False

        # source queue
        self.__frame_queue = VFAIQueue(qsize)

        # general config object
        self.__config = config

        # opencv video capture obj
        self.__cap: cv2.VideoCapture | None = None

        self.__logger = logging.getLogger(__name__)

        self.__frame_count = 0

    def start(self):
        if self.__thread and self.__thread.is_alive():
            return
        self.__stop_event.clear()
        self.__thread = threading.Thread(target=self.__run, name=self.__name)
        self.__thread.start()

    def stop(self):
        if not self.__stop_called:
            self.__stop_called = True
            self.__stop()
            self.__stop_called = False

    def get_frame(self):
        try:
            frame = self.__frame_queue.dequeue()
            # if self.__config.verbose and frame is not None:# and self.__frame_count - frame > 1000:
            #     self.__logger.debug(f'Dequeued frame ID{frame._id}. Framecount {self.__frame_count}; '
            #                         f'Diff {self.__frame_count-frame._id}.')
            return frame
        finally:
            pass

    def __run(self):
        try:
            self.__run_impl()
        finally:
            self.__cleanup()

    def __stop(self):
        self.__stop_event.set()
        if self.__thread:
            self.__thread.join()
        self.__thread = None

    def __cleanup(self):
        self.__deinit_source()

    def __deinit_source(self):
        if self.__cap is not None:
            self.__cap.release()
            self.__logger.warning('Source released.')
            self.__cap = None

    def __run_impl(self):
        self.__init_source()
        try:
            start = time.time()
            if self.__config.verbose:
                    self.__logger.debug(f'Starting grabbing at {time.time()}')
            while not self.__stop_event.is_set():
                if self.__cap is None:
                    raise ValueError('Capture object is None')
                ret, frame = self.__cap.read()
                if not ret:
                    if self.__config.reconnect_source_on_failure:
                        self.__deinit_source()
                        self.__logger.info(f'Will reconnect source.')
                        self.__init_source()
                        continue
                    else:
                        self.__logger.error(f'Will not reconnect source.')
                        break
                vframe = VFAIFrame(id=self.__frame_count,
                                   data=frame,
                                   since_start=time.time() - start,
                                   epoch=time.time()
                                   )
                if self.__config.target.width > 0 and self.__config.target.height > 0:
                    frame = cv2.resize(frame, (self.__config.target.width, self.__config.target.height))
                self.__frame_queue.enqueue(vframe)
                self.__frame_count += 1
                # if self.__config.verbose and self.__frame_count % 1000 == 0:
                #     self.__logger.debug(f'Enqueued {self.__frame_count} frames.')
        finally:
            if self.__config.verbose:
                self.__logger.debug(f'Deinitialize source at {time.time()}')
            self.__deinit_source()

    def __init_source(self):
        self.__logger.info('Initializing source...')
        self.__cap = cv2.VideoCapture(self.__config.source.url)

        if self.__cap is None:
            raise ValueError('Could not initialize source!')
            return

        # after init, set values to source
        self.__config.source.width = int(self.__cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.__config.source.height = int(self.__cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.__cap.get(cv2.CAP_PROP_FPS)
        self.__config.source.fps = int(round(fps)) if fps > 0 else 25  # fallback
        self.__config.source.aspect_ratio = self.__config.source.width / self.__config.source.height
        self.__logger.info(f"Source frame dimensions: {self.__config.source.width:.0f} x {self.__config.source.height:.0f}, "
              f"Aspect ratio: {self.__config.source.aspect_ratio:.0f}, FPS: {self.__config.source.fps:.0f}")

        if self.__config.target.width > 0 and self.__config.target.height > 0:
            scale = min(self.__config.target.width / self.__config.source.width,
                        self.__config.target.height / self.__config.source.height)
            self.__config.target.width = int(self.__config.source.width * scale)
            self.__config.target.height = int(self.__config.source.height * scale)
            self.__logger.info(f"New frame dimensions: {self.__config.target.width} x {self.__config.target.height}")
        else:
            self.__logger.info(f"No target frame dimensions set. Using source dimensions. {self.__config.source.width} x {self.__config.source.height}")

        # if there is no specific ROI saved; use the full frame
        if not self.__config.roi.is_set():
            if self.__config.target.width > 0 and self.__config.target.height > 0:
                self.__config.roi = (0, 0, self.__config.target.width, self.__config.target.height)
                self.__logger.info(f"ROI Set to target dimensions: (0, 0) to ({self.__config.target.width}, {self.__config.target.height})")
            else:
                self.__config.roi = (0, 0, self.__config.source.width, self.__config.source.height)
                self.__logger.info(f"ROI Set to source dimensions: (0, 0) to ({self.__config.source.width}, {self.__config.source.height})")
        else:
            x1, y1 = self.__config.roi.top_left.xy
            x2, y2 = self.__config.roi.bottom_right.xy
            self.__logger.info(f"ROI already set to: f({x1}, {y1}), ({x2}, {y2})")