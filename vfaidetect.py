import logging
import numpy as np
from ultralytics import YOLO
from vfaiconfig import VFAIConfig

class VFAIDetector:
    def __init__(self, config: VFAIConfig):
        self.__config = config
        self.__model = YOLO(self.__config.model)
        self.__warmed_up = False
        self.__logger = logging.getLogger(__name__)
    
    def __warmup(self):
        dummy = np.zeros((self.__config.source.height, self.__config.source.width, 3), dtype=np.uint8)
        for _ in range(5):
            self.__model(dummy, verbose=False)

    def detect(self, frame):
        if not self.__warmed_up:
            self.__logger.info('Engine warmup started.')
            self.__warmup()
            self.__logger.info('Engine warmup completed.')
            self.__warmed_up = True
        return self.__model(frame,
                            verbose=False, # self.__config.verbose,
                            conf=self.__config.threshold)

    def get_class_name(self, cls_id):
        return self.__model.names[cls_id]