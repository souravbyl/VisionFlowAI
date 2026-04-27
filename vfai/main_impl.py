import os
import cv2
import sys
import time
import signal
import logging
import threading
from queue import Queue
from vfai.loggermgr import LoggerManager
from vfai.engine import Engine
from vfai.config_loader import load_config
from vfai.metrics.aggregator import MetricsAggregator
from vfai.metrics.logger import aggregator_loop, logger_loop


def engine_loader(config_file):
    print(f"Working Directory: {os.getcwd()}")
    print(f"Loading configurations from: {config_file}")

    # loading config file
    config = load_config(config_file)

    # initialize logger
    loggermgr = LoggerManager(
        log_file="logs/VisionFlowAI.log",
        level=config.loglevel,
        when="midnight",  # rotate daily
        backup_count=7,  # keep 7 days
    )
    loggermgr.start()

    # logging related variables
    logger = logging.getLogger(__name__)

    # logging library versions
    logger.critical(f"OpenCV Version: {cv2.__version__}")

    # global stop event.
    # all the threads will wait for this event to set.
    # remember: if this is set by any of the threads, all the threads will stop.
    stop_event = threading.Event()
    stop_event.clear()

    # metrics related variables and threads
    metrics_q = Queue()
    aggregator = MetricsAggregator()
    metrics_threads = [
        threading.Thread(
            target=aggregator_loop,
            args=(metrics_q, aggregator, stop_event),
            daemon=True,
        ),
        threading.Thread(
            target=logger_loop, args=(aggregator, stop_event), daemon=True
        ),
    ]

    # engine related variables
    engine = Engine(config=config, metrics_q=metrics_q, stop_event=stop_event)

    # termination handle - start
    def shutdown(signum, frame):
        logger.info(f"Signal {signum} received, shutting down...")
        stop_event.set()
        for t in metrics_threads:
            t.join()
        engine.join()
        # exit log
        logger.info("exiting gracefully.")
        # on shutdown
        loggermgr.stop()
        sys.exit(0)

    # register signals
    signal.signal(signal.SIGINT, shutdown)  # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown)  # kill command
    # termination handle - end

    # start the threads
    for t in metrics_threads:
        t.start()
    engine.start()

    # wait for stop event
    while not stop_event.wait(timeout=1):
        time.sleep(1)
