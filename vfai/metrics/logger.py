import threading
import time
import logging


def aggregator_loop(metrics_q, aggregator, stop_event: threading.Event):
    logger = logging.getLogger("aggregator_loop")
    logger.debug("started")
    while not stop_event.is_set():
        try:
            ev = metrics_q.get()
            aggregator.process_event(ev)
        except Exception as e:
            logger.critical(f"exception {e}")
    logger.debug("stopped")


def logger_loop(aggregator, stop_event: threading.Event):
    logger = logging.getLogger("logger_loop")
    logger.debug("started")
    skip_count = 0
    max_skip_count = 50
    while not stop_event.is_set():
        time.sleep(1)
        skip_count += 1
        if skip_count % max_skip_count != 0:
            continue
        skip_count = 0
        snap = aggregator.snapshot()
        for stage, m in snap.items():
            logger.info(
                f"[{stage}] FPS={m['fps']} in={m['in']} out={m['out']} drop={m['drop']} "
                f"proc={m['proc_ms']}ms queue={m['queue_ms']}ms total={m['total_ms']}ms"
            )
    logger.debug("stopped")
