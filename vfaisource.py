import cv2
from vfaiconfig import VFAIConfig
from vfaistat import VFAIStat

class VFAISource:
    def __init__(self, config: VFAIConfig):
        self._cap = None
        self._config = config
        self._stat = VFAIStat()
        self._init_source()

    def _deinit_source(self):
        if self._cap:
            self._cap.release()
        print('Source released.')
    
    def _init_source(self):
        print('Initializing source...')
        self._deinit_source()
        self._cap = cv2.VideoCapture(self._config.get_source())
        self._src_width = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self._src_height = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self._src_fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._src_aspect_ratio = self._src_width / self._src_height
        print(f"Source frame dimensions: {self._src_width} x {self._src_height}, "
              f"Aspect ratio: {self._src_aspect_ratio}, FPS: {self._src_fps}")

        scale = min(self._config._get_target_width() / self._src_width,
                    self._config._get_target_height() / self._src_height)
        self._new_w = int(self._src_width * scale)
        self._new_h = int(self._src_height * scale)
        print(f"New frame dimensions: {self._new_w} x {self._new_h}")
    
    def frame_generator(self):
        try:
            while True:
                self._stat.add_in()
                ret, frame = self._cap.read()
                if not ret:
                    self._stat.add_err()
                    self._init_source()
                    continue
                self._stat.add_ok()
                frame = cv2.resize(frame, (self._new_w, self._new_h))
                yield frame
        finally:
            self._deinit_source()