import signal
import sys
from vfaiconfig import VFAIConfig
from vfaiengine import VFAIEngine

def main():
    engine = None
    def shutdown(signum, frame):
        print(f"Signal {signum} received, shutting down...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)   # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown)  # kill command

    config = VFAIConfig()
    config._source = 'C:/Users/soura/Downloads/15192700-sd_240_426_30fps.mp4'
    config._source = 'C:/Users/soura/Downloads/14778909_640_360_60fps.mp4'
    config._source = 'C:/Users/soura/Downloads/istockphoto-1162603138-640_adpp_is.mp4'
    config._target_height = 256
    config._target_width = 256
    config._target_fps = 10
    config._model = "yolov8n.pt"
    config._threshold = 0.3
    config._drop_frames_to_match_in_fps = True
    engine = VFAIEngine(config=config)

    engine.start()
    while True:
        pass

if __name__ == "__main__":
    main()