import time
import cv2
from vfaiconfig import VFAIConfig
from vfaistat import VFAIStat
from vfaisource import VFAISource
from vfaidetect import VFAIDetector

class VFAIEngine:
    def __init__(self, config: VFAIConfig):
        self._config = config
        self._stat = VFAIStat()
        self._source = VFAISource(self._config)
        self._detector = VFAIDetector(self._config)
    
    def start(self):
        gen = self._source.frame_generator()

        objects = {}
        occurances = {}

        id = 0
        frame_count = 0
        start = time.time()

        threshold = 0.6

        for frame in gen:
            frame_count += 1
            # showing something on the frame to make sure it's working
            # cv2.putText(frame, f"Something: ", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            # perform object detection
            results = self._detector.detect(frame=frame)
            r = results[0]
            boxes = r.boxes
            
            for box in boxes:
                cls_id = int(box.cls[0])                # class index
                conf = float(box.conf[0])               # confidence
                name = r.names[cls_id]                  # class name
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # bounding box coordinates

                if conf > threshold:
                    objects[name] = objects.get(name, 0) + 1
                    occurances[id] = {
                        'name': name,
                        'class_id': cls_id,
                        'confidence': f'{conf:.2f}',
                        "rel_timestamp": f'{time.time() - start:.2f}',
                        "absolute_timestamp": f'{time.time():.0f}'
                    }
                    id += 1

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"{name} {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # annotated = results[0].plot()
            # cv2.imwrite(f"output_{frame_count}.jpg", annotated)
            # cv2.imshow("YOLO", annotated)

            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) == ord('q'):
                break

        print("Final object counts:", objects)
        print("Occurances:", occurances)
        cv2.destroyAllWindows()
        print("Destroyed")
    