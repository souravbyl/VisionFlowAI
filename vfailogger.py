import logging
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from queue import Queue


class LoggerManager:
    def __init__(
        self,
        log_file: str = "VisionFlowAI.log",
        level: int = logging.INFO,
        when: str = "midnight",  # "S", "M", "H", "D", "midnight"
        interval: int = 1,
        backup_count: int = 7,  # keep last 7 rotations
    ):
        self.log_queue = Queue()

        # =========================
        # Formatter
        # =========================
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s "
            "[%(filename)s:%(lineno)d:%(funcName)s] %(message)s"
        )

        # =========================
        # File handler (time-based rotation)
        # =========================
        file_handler = TimedRotatingFileHandler(
            log_file,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)

        # Optional: better filename suffix
        file_handler.suffix = "%Y-%m-%d"

        # =========================
        # Console handler
        # =========================
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)

        # =========================
        # Queue-based logging (non-blocking)
        # =========================
        queue_handler = QueueHandler(self.log_queue)

        self.listener = QueueListener(
            self.log_queue,
            file_handler,
            console_handler,
            respect_handler_level=True,
        )

        # =========================
        # Root logger setup
        # =========================
        self.logger = logging.getLogger()
        self.logger.setLevel(level)
        self.logger.handlers.clear()
        self.logger.addHandler(queue_handler)

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()
