import cv2
import logging
from vfaiconfig import VFAIConfig


class VFAITracker:
    def __init__(self, config: VFAIConfig, description: str = "") -> None:
        self.__config = config
        self.__tracker = None

        self.__logger = logging.getLogger(f"{__name__}_{description}")

        if not self.__config.tracker_name:
            self.__logger.critical(
                f"Seems tracker name is not defined. {self.__config.tracker_name}"
            )
        elif self.__config.tracker_name == "cv2_TrackerKCF":
            self.__tracker = cv2.TrackerKCF_create()
            self.__logger.info(f"Tracker {self.__config.tracker_name} created.")
        elif self.__config.tracker_name == "cv2_TrackerCSRT":
            self.__tracker = cv2.TrackerCSRT_create()
            self.__logger.info(f"Tracker {self.__config.tracker_name} created.")

    def init(self, frame, bbox):
        if self.__tracker is None:
            self.__logger.error(f"No tracker is initialized.")
            raise ValueError("No tracker is initialized.")
        self.__tracker.init(frame, bbox)  # bbox = (x, y, w, h)

    def update(self, frame):
        if self.__tracker is None:
            self.__logger.error(f"No tracker is initialized.")
            raise ValueError("No tracker is initialized.")
        # update (every frame)
        success, bbox = self.__tracker.update(frame)
        return success, bbox
