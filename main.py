import cv2
import sys
import signal
import logging
from vfaiconfig import VFAIConfig
from vfaiengine import VFAIEngine

def main():

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    logging.basicConfig(
        filename="VisionFlowAI.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    logger = logging.getLogger(__name__)

    logger.error(cv2.__version__)

    x1, y1, x2, y2 = None, None, None, None

    # source = 'C:/Users/soura/Downloads/15192700-sd_240_426_30fps.mp4'
    # source = 'C:/Users/soura/Downloads/14726843_360_640_30fps.mp4'
    # source = 'C:/Users/soura/Downloads/istockphoto-1162603138-640_adpp_is.mp4'
    # source = 'C:/Users/soura/Downloads/VID_20260414_095729357.mp4'

    source = 'C:/Users/soura/Downloads/sb/Channel ID_18_3.mp4'
    # source = 'C:/Users/soura/Downloads/sb/Channel ID_20_1.mp4'

    # source = 'rtsp://admin:admin@123@192.168.0.150/cam/realmonitor?channel=01&subtype=00'
    # x1, y1, x2, y2 = 922, 284, 1129, 502
    
    # source = 'rtsp://admin:admin@123@192.168.0.150/cam/realmonitor?channel=01&subtype=01'
    # x1, y1, x2, y2 = 160, 75, 211, 131

    config = VFAIConfig()

    config.debug = True
    config.verbose = config.debug
    config.dump_results = True
    config.results_dump_path = 'dumps'

    config.model = "yolov8n.pt"
    config.threshold = 0.7
    config.d_imshow = True

    config.source.url = source
    config.reconnect_source_on_failure = False
    config.source_imshow = True
    config.drop_frames_to_match_in_fps = False
    if x1 is not None:
        config.roi = (x1, y1, x2, y2)

    # config.target = config.source.url, 256, 256, 10

    config.motion_percent = 0.001
    config.motion_imshow_threshold = False

    config.enable_tracker = True
    config.tracker_name = 'cv2_TrackerCSRT'

    engine = VFAIEngine(config=config)

    # termination handle - start
    def shutdown(signum, frame):
        logger.info(f"Signal {signum} received, shutting down...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)   # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown)  # kill command
    # termination handle - end

    engine.start()

    while True:
        pass

if __name__ == "__main__":
    main()