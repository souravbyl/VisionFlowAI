import cv2
import threading
import time
from vfaiconfig import VFAIConfig
from vfaistat import VFAIStat
from vfaiqueue import VFAIQueue
from vfaiframe import VFAIFrame

class VFAISource:
    def __init__(self, config: VFAIConfig, qsize=10, name="Worker-VFAISource"):
        self.name = name
        self._stop_event = threading.Event()
        self._thread = None

        self._qsize = qsize
        self._cap = None
        self._config = config
        self._stat = VFAIStat()
        self._frame_queue = VFAIQueue(qsize)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=self.name)
        self._thread.start()

    def _run(self):
        try:
            self.run()
        finally:
            self.cleanup()

    def run(self):
        self._init_source()
        try:
            start = time.time()
            while not self._stop_event.is_set():
                self._stat.add_in()
                ret, frame = self._cap.read()
                if not ret:
                    self._stat.add_err()
                    self._deinit_source()
                    self._init_source()
                    continue
                self._stat.add_ok()
                frame = cv2.resize(frame, (self._new_w, self._new_h))
                vframe = VFAIFrame(data=frame,
                                   since_start=time.time() - start,
                                   epoch=time.time()
                                   )
                self._frame_queue.enqueue(vframe)
        finally:
            self._deinit_source()
            pass

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def should_stop(self):
        return self._stop_event.is_set()

    def cleanup(self):
        self._deinit_source()

    def _deinit_source(self):
        if self._cap:
            self._cap.release()
            print('Source released.')
            self._cap = None
    
    def _init_source(self):
        print('Initializing source...')
        self._deinit_source()
        self._cap = cv2.VideoCapture(self._config.get_source())
        self._src_width = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self._src_height = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._src_fps = int(round(fps)) if fps > 0 else 30  # fallback
        self._src_aspect_ratio = self._src_width / self._src_height
        print(f"Source frame dimensions: {self._src_width} x {self._src_height}, "
              f"Aspect ratio: {self._src_aspect_ratio}, FPS: {self._src_fps}")

        scale = min(self._config._get_target_width() / self._src_width,
                    self._config._get_target_height() / self._src_height)
        self._new_w = int(self._src_width * scale)
        self._new_h = int(self._src_height * scale)
        print(f"New frame dimensions: {self._new_w} x {self._new_h}")

        self._config._source_fps = self._src_fps
        
    
    def get_frame(self):
        try:
            frame = self._frame_queue.dequeue()
            return frame
        finally:
            pass