import threading
import time
import cv2
from vfaiconfig import VFAIConfig
from vfaiframe import VFAIFrame
from vfaistat import VFAIStat
from vfaisource import VFAISource
from vfaidetect import VFAIDetector

class VFAIEngine:
    def __init__(self, config: VFAIConfig, name="Worker-VFAIEngine"):
        self.name = name
        self._stop_event = threading.Event()
        self._thread = None

        self._config = config
        self._stat = VFAIStat()
        self._source = VFAISource(config=self._config, qsize=360000)
        self._detector = VFAIDetector(config=self._config)

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
        self._source.start()

        # objects = {}
        # occurances = {}

        detection_id = 0
        # object_id = 0

        while not self._stop_event.is_set():
            vframe = self._source.get_frame()
            if vframe is None:
                time.sleep(1/1000)
                continue
            detection_id += 1
            
            # cv2.putText(frame, f"Something: ", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            # perform object detection
            detection_startT = time.time()
            results = self._detector.detect(frame=vframe._data)
            detection_endT = time.time()
            if results is None or len(results) == 0:
                continue
            r = results[0]
            boxes = r.boxes
            if len(boxes) == 0:
                continue

            # object_id = 0
            nowt = time.time()
            elapsed = nowt-vframe._epoch

            to_drop = 0
            if self._config._is_drop_frames_to_match_in_fps():
                to_drop = int((elapsed * 1000)/(1000/self._config.get_source_fps()))

            print(f'captured at {vframe._epoch:.0f}, detected at {nowt:.0f} '
                  f'Diff {elapsed:.0f}s, '
                  f'Inference Time {(detection_endT-detection_startT):.2f}s, '
                  f'Source FPS: {self._config.get_source_fps()}, '
                  f'to_drop: {to_drop} frames, '
                  )
            
            # to_drop -= int(to_drop*0.20)
            if self._config._is_drop_frames_to_match_in_fps():
                for _ in range(to_drop):
                    self._source.get_frame()
                print(f'Dropped {to_drop} frames')

        
            # for box in boxes:
            #     frame = vframe._data
            #     box_count += 1
            #     cls_id = int(box.cls[0])                # class index
            #     conf = float(box.conf[0])               # confidence
            #     name = r.names[cls_id]                  # class name
            #     x1, y1, x2, y2 = map(int, box.xyxy[0])  # bounding box coordinates

            #     if True or conf > threshold:
            #         occurances[id] = {
            #             'id': id,
            #             'name': name,
            #             'class_id': cls_id,
            #             'confidence': f'{conf:.2f}',
            #             "since_start": f'{vframe._since_start:.2f}',
            #             "epoch": f'{vframe._epoch:.0f}',
            #             "detected_at": f'{nowt:.0f}'
            #         }
            #         id += 1

                    # cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # label = f"{name} {conf:.2f}"
                    # cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    # cv2.imwrite(f"output_{frame_count}_box_{box_count}.jpg", frame)
                    # cv2.imshow("YOLO", frame)

            # annotated = results[0].plot()
            # cv2.imwrite(f"output_{frame_count}.jpg", annotated)
            # cv2.imshow("YOLO", annotated)

            # cv2.imshow("Frame", frame)
            # if cv2.waitKey(1) == ord('q'):
            #     break

        # print("Final object counts:", objects)
        # print("Occurances:", occurances)
        # cv2.destroyAllWindows()
        print("Destroyed")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def should_stop(self):
        return self._stop_event.is_set()

    def cleanup(self):
        self._source.stop()
    