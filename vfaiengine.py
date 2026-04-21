import cv2
import json
import time
import psutil
import logging
import threading
import numpy as np

from cv_util import CV_Show

from vfaicolorcode import COLOR_MOTION, COLOR_TRACK, COLOR_DETECT, COLOR_DEBUG
from vfairoi import VFAIROI
from vfaiframe import VFAIFrame
from vfaimotion import VFAIMotion
from vfaiconfig import VFAIConfig
from vfaisource import VFAISource
from vfaidetect import VFAIDetector
from vfaitracker import VFAITracker

class VFAIEngine:
    def __init__(self, config: VFAIConfig, name="Worker-VFAIEngine"):
        self.__name = name
        self.__stop_event = threading.Event()
        self.__thread = None
        self.__config = config
        self.__source = VFAISource(config=self.__config, qsize=360000)
        self.__detector = VFAIDetector(config=self.__config)
        self.__motion = VFAIMotion(config=self.__config)
        self.__logger = logging.getLogger(__name__)

    def start(self):
        if self.__thread and self.__thread.is_alive():
            return
        self.__stop_event.clear()
        self.__thread = threading.Thread(target=self.__run, name=self.__name)
        self.__thread.start()

    def __run(self):
        try:
            self.__run_impl()
        finally:
            self.__cleanup()

    def __run_impl(self):
        self.__source.start()

        objects = {}
        occurances = {}

        detection_id = 0

        tracker = None
        tracking = False
        # last_detect_frame = 0
        # redirect_interval = 100

        while not self.__stop_event.is_set():

            if self.__config.debug:
                # self.__logger.debug(psutil.virtual_memory())

                if cv2.waitKey(1) == ord('q'):
                    pass

            vfaiframe = self.__source.get_frame()
            if vfaiframe is None:
                time.sleep(1/1000)
                continue

            # extract the region we are interested in
            roi_x1, roi_y1 = self.__config.roi.top_left.xy
            roi_x2, roi_y2 = self.__config.roi.bottom_right.xy

            # if self.__config.debug:
            #     self.__logger.info(f'ROI: ({roi_x1}, {roi_y1}), ({roi_x2}, {roi_y2})')

            x, y, w, h = roi_x1, roi_y1, (roi_x2-roi_x1), (roi_y2-roi_y1)
            roiframe = vfaiframe._data[y:y+h, x:x+w]

            if self.__config.source_imshow:
                CV_Show("Source", roiframe)
            
            motion_startT = time.time()
            grayscale = self.__motion.get_grayscale(roiframe)
            motion_detected, bbox = self.__motion.check_if_motion(grayscale, w, h)
            motion_endT = time.time()

            if motion_detected == False or bbox is None:
                if self.__config.debug:
                    pass
                continue

            motion_x, motion_y, motion_w, motion_h = bbox
            motion_x1, motion_y1 = motion_x+motion_w, motion_y+motion_h
            motion_roi = roiframe[motion_y:motion_y1, motion_x:motion_x1]
            
            # if self.__config.debug:
            #     # self.__logger.debug(f'Motion detected at ({motion_x}, {motion_y}), ({motion_x1}, {motion_y1}), '
            #     #                     f'Motion Detection Time {(motion_endT-motion_startT):.2f}s')
            #     if self.__config.d_imshow:
            #         # CV_Show("Motion(Cropped)", motion_roi)
            #         # cv2.rectangle(roiframe, (motion_x, motion_y), (motion_x1, motion_y1), COLOR_MOTION, 2)
            #         CV_Show("Motion(Full Frame)", roiframe)

            # =========================================================
            # TRACKING MODE
            # =========================================================
            if self.__config.enable_tracker and tracking and tracker is not None:
                ok, trackerbbox = tracker.update(roiframe)
                if ok:
                    # x, y, w, h = map(int, trackerbbox)
                    # cv2.rectangle(roiframe, (x, y), (x+w, y+h), COLOR_TRACK, 2)
                    # if self.__config.d_imshow:
                    #     CV_Show("Tracking", roiframe)

                    # if vfaiframe._id - last_detect_frame > redirect_interval:
                    #     self.__logger.debug('tracker left for redirection reason')
                    #     tracking = False
                    # else:
                    #     # self.__logger.debug('tracking..')
                    #     pass
                    pass
                else:
                    self.__logger.debug('tracker left as new object')
                    tracking = False

            # perform object detection
            if not tracking and bbox:

                # if self.__config.debug:
                #     self.__logger.debug('Calling detector')

                detection_startT = time.time()
                results = self.__detector.detect(frame=motion_roi)
                detection_endT = time.time()

                # if self.__config.debug:
                #     self.__logger.debug('Response from detector')

                nowt = time.time()
                elapsed = nowt-vfaiframe._epoch

                to_drop = 0
                if self.__config.drop_frames_to_match_in_fps:
                    to_drop = int((elapsed * 1000)/(1000/self.__config.source.fps))

                # if self.__config.debug:
                #     self.__logger.info(f'captured at {vfaiframe._epoch:.0f}, detected at {nowt:.0f} '
                #         f'Diff {elapsed:.0f}s, '
                #         f'Inference Time {(detection_endT-detection_startT):.2f}s, '
                #         f'Source FPS: {self.__config.source.fps}, '
                #         f'to_drop: {to_drop} frames, '
                #         )
                
                to_drop -= int(to_drop*0.20)
                if self.__config.drop_frames_to_match_in_fps:
                    for _ in range(to_drop):
                        self.__source.get_frame()
                    self.__logger.error(f'Dropped {to_drop} frames')

                if results is None or len(results) == 0:
                    continue

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
                    conf = float(scores[i])
                    cls_id = int(class_ids[i])
                    cls_name = self.__detector.get_class_name(cls_id)

                    # if self.__config.debug:
                    #     self.__logger.debug(f'Event detected at ({dx1}, {dy1}), ({dx2}, {dy2})')
                    #     if self.__config.d_imshow:
                    #         # cv2.rectangle(motion_roi, (dx1, dy1), (dx2, dy2), COLOR_DETECT, 2)
                    #         CV_Show("Detection", motion_roi)
                    
                    # map to roiframe
                    dx1_full = int(motion_x + dx1)
                    dy1_full = int(motion_y + dy1)
                    dx2_full = int(motion_x + dx2)
                    dy2_full = int(motion_y + dy2)

                     # -------- INIT TRACKER --------
                    tracker = VFAITracker(self.__config, description=f'tracker_{vfaiframe._id}')
                    tracker.init(roiframe, (dx1_full, dy1_full, int(dx2_full - dx1_full), int(dy2_full - dy1_full)))
                    tracking = True
                    # last_detect_frame = vfaiframe._id
                    self.__logger.debug(f'Tracker {vfaiframe._id} started.')
                    
                    occ = {
                        'name': cls_name,
                        'class_id': cls_id,
                        'confidence': f'{conf:.2f}',
                        "since_start": f'{vfaiframe._since_start:.2f}',
                        "epoch": f'{vfaiframe._epoch:.0f}',
                        "detected_at": f'{nowt:.0f}',
                        'input_frame_id': f'{vfaiframe._id}'
                    }

                    occurances[detection_id] = occ
                    objects[cls_name] = objects.get(cls_name, 0) + 1

                    occ_str = json.dumps(occ)
                    self.__logger.info(occ_str)
                    self.__logger.info(f'{cls_name} ++ ====> {objects[cls_name]}')

                    if self.__config.debug:
                        cv2.rectangle(roiframe, (dx1_full, dy1_full), (dx2_full, dy2_full), COLOR_DETECT, 2)
                        cv2.putText(roiframe,
                                    f"{cls_name} {conf:.2f}",
                                    (dx1_full, dy1_full - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_DETECT, 2)

                        if self.__config.d_imshow:
                            CV_Show("Detection(Full)", roiframe)

                    # Dump image and json
                    if self.__config.dump_results:
                        fname = f"F{vfaiframe._id}-D{detection_id}_C{cls_name}-P{conf:.0f}"
                        if len(self.__config.results_dump_path) > 0:
                            fname = f"{self.__config.results_dump_path}/{fname}"
                        cv2.imwrite(f"{fname}.jpg", roiframe)
                        # cv2.imwrite(f"{fname}_full.jpg", vfaiframe._data)
                        with open(f"{fname}.json", "w") as f:
                            json.dump(occ, f)
                            # self.__logger.info(f'Detection saved in {fname}.json')
                
                    detection_id += 1

    def stop(self):
        self.__stop_event.set()
        if self.__thread:
            self.__thread.join()

    def __cleanup(self):
        self.__source.stop()
        if self.__config.debug:
            cv2.destroyAllWindows()
            self.__logger.info("Destroyed")
    