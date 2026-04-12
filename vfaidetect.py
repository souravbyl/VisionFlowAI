import numpy as np
from ultralytics import YOLO
from vfaiconfig import VFAIConfig
from vfaistat import VFAIStat

class VFAIDetector:
    def __init__(self, config: VFAIConfig):
        self._config = config
        self._stat = VFAIStat()
        self._model = YOLO(self._config.get_model())
        self._warmup()
    
    def _warmup(self):
        dummy = np.zeros((256, 256, 3), dtype=np.uint8)
        for _ in range(5):
            self._model(dummy, verbose=False)

    def detect(self, frame, threshold=None):
        self._stat.add_in()
        results = self._model(frame,
                              verbose=self._config.get_verbosity(),
                              conf=self._config.get_threshold() if threshold is None else threshold)
        if len(results[0].boxes):
            self._stat.add_ok()
        else:
            self._stat.add_err()
        return results