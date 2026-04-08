from vfaiconfig import VFAIConfig
from vfaiengine import VFAIEngine

config = VFAIConfig()
config._source = 'C:/Users/soura/Downloads/15192700-sd_240_426_30fps.mp4'
config._source = 'C:/Users/soura/Downloads/14778909_640_360_60fps.mp4'
config._source = 'C:/Users/soura/Downloads/istockphoto-1162603138-640_adpp_is.mp4'
config._target_height = 414
config._target_width = 414
config._target_fps = 10
config._model = "yolov8s.pt"
config._threshold = 0.3
engine = VFAIEngine(config=config)

engine.start()
print("End.")