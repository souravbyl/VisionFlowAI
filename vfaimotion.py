import cv2
import numpy as np

from cv_util import CV_Show
from vfaiconfig import VFAIConfig


class VFAIMotion:
    def __init__(self, config: VFAIConfig) -> None:
        self.__config = config
        self.__prev_gray = None
        self.__kernel = np.ones((3, 3), np.uint8)

    def get_grayscale(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        return gray

    def check_if_motion(self, gray, w, h):
        if self.__prev_gray is None:
            self.__prev_gray = gray
            return False, None

        # Frame differencing
        diff = cv2.absdiff(self.__prev_gray, gray)

        # Binary threshold (motion areas become white)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        # Remove noise (expand white regions)
        thresh = cv2.dilate(thresh, self.__kernel, iterations=2)

        if self.__config.imshow_motion_threshold:
            CV_Show("Threshold", thresh)

        # Compute motion score
        motion_pixels = cv2.countNonZero(thresh)

        self.__prev_gray = gray

        if motion_pixels is None:
            return False, None

        if (motion_pixels / (w * h)) > self.__config.motion_percent:
            # motion is there

            # find bbox
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            bboxes = []

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 500:  # filter noise (tune this)
                    continue

                x, y, w, h = cv2.boundingRect(cnt)
                bboxes.append((x, y, w, h))

            if len(bboxes) == 0:
                return False, None

            # Merge boxes
            x_min = min([x for x, y, w, h in bboxes])
            y_min = min([y for x, y, w, h in bboxes])
            x_max = max([x + w for x, y, w, h in bboxes])
            y_max = max([y + h for x, y, w, h in bboxes])

            merged_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

            # Add padding
            pad = 40
            x, y, w, h = merged_bbox

            x = max(0, x - pad)
            y = max(0, y - pad)
            w = w + 2 * pad
            h = h + 2 * pad

            return True, (x, y, w, h)
        else:
            return False, None
