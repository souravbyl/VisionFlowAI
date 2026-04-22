import cv2
import json
import time
import logging
import threading
from vfaiconfig import VFAIConfig
from vfaiqueue import VFAIQueue


class VFAIEventDispatcher:
    def __init__(self, config: VFAIConfig, qsize: int=10, name: str="VFAIEventDispatcher") -> None:
        # class internals
        self.__name: str = name

        #config
        self.__config = config

        # thread/event related
        self.__thread = None
        self.__stop_event = threading.Event()
        self.__stop_called = False

        # event queue
        self.__event_queue = VFAIQueue(qsize)

        self.__logger = logging.getLogger(f'{__name__}')
    
    def dispatch_event(self, vfaiframe, detection_id, class_id, class_name, confidence, eventtime, snap, bbox):
        event = {
            'id': detection_id,
            'class_name': class_name,
            'class_id': class_id,
            'confidence': f'{confidence:.2f}',
            "since_start": f'{vfaiframe._since_start:.2f}',
            "epoch": f'{vfaiframe._epoch:.0f}',
            "detected_at": f'{eventtime:.0f}',
            'input_frame_id': f'{vfaiframe._id}',
            'snap': snap
        }
        self.__event_queue.enqueue(event)

    def start(self):
        if self.__thread and self.__thread.is_alive():
            return
        self.__stop_event.clear()
        self.__thread = threading.Thread(target=self.__run, name=self.__name)
        self.__thread.start()

    def stop(self):
        if not self.__stop_called:
            self.__stop_called = True
            self.__stop()
            self.__stop_called = False

    def __run(self):
        try:
            self.__run_impl()
        finally:
            self.__cleanup()

    def __stop(self):
        self.__stop_event.set()
        if self.__thread:
            self.__thread.join()
        self.__thread = None

    def __cleanup(self):
        pass

    def __run_impl(self):
        start = time.time()
        if self.__config.verbose:
            self.__logger.debug(f'Dispatcher thread started at {start}')
        try:
            while not self.__stop_event.is_set():
                event = self.__event_queue.dequeue()
                if event is None:
                    continue
                
                snap = event['snap']
                event.pop('snap', None)
                event_str = json.dumps(event)
                self.__logger.info(event_str)
                
                # Dump image and json
                if self.__config.dump_results:
                    fname = f"F{event['input_frame_id']}-D{event['id']}_C{event['class_name']}-P{event['confidence']}"
                    if len(self.__config.results_dump_path) > 0:
                        fname = f"{self.__config.results_dump_path}/{fname}"
                    cv2.imwrite(f"{fname}.jpg", snap)
                    with open(f"{fname}.json", "w") as f:
                        json.dump(event, f)
                        if self.__config.verbose:
                            self.__logger.info(f'Detection saved in {fname}.json')
        finally:
            if self.__config.verbose:
                self.__logger.debug(f'Dispatcher thread ended at {time.time()}')