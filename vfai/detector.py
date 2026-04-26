import logging

import numpy as np
from ultralytics import YOLO

from vfai.config import Config


class Detector:
    def __init__(self, config: Config):
        self.__config = config
        self.__model = YOLO(self.__config.model)
        self.__logger = logging.getLogger(__name__)

    def warmup(self):
        self.__logger.debug("Engine warmup started.")
        dummy = np.zeros(
            (self.__config.source.height, self.__config.source.width, 3), dtype=np.uint8
        )
        verbose = True if self.__config.debug and self.__config.loglevel == logging.DEBUG else False
        for _ in range(5):
            self.__model(dummy, verbose=verbose)
        self.__logger.debug("Engine warmup completed.")

    def detect(self, frame):
        verbose = True if self.__config.debug and self.__config.loglevel == logging.DEBUG else False
        return self.__model(frame, verbose, conf=self.__config.threshold)

    def get_class_name(self, cls_id):
        return self.__model.names[cls_id]
