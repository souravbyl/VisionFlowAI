import logging
from vfairoi import VFAIROI
from vfaistreamprop import VFAIStreamProp

class VFAIConfig:
    def __init__(self):

        self.__logger = logging.getLogger(__name__)

        ######################################################################################
        ############################# Common Config ##########################################
        ######################################################################################
        self.__c_debug: bool = False            # Kill switch for overall debug level
        self.__c_verbose: bool = False          # If true, more logs will come
        self.__c_dump_results = False           # If true, results will be dumped in json and jpg
        self.__c_results_dump_path = 'dumps'    # results will be dumped in this directory

        ######################################################################################
        ############################# AI model/detection related #############################
        ######################################################################################
        self.__d_model_name: str = ''       # model name
        self.__d_threshold: float = 0.8     # minimum confidence we will allow
        self.__d_imshow: bool = False       # imshow the detection results

        ######################################################################################
        ############################# Source related #########################################
        ######################################################################################
        self.__source: VFAIStreamProp = VFAIStreamProp()    # actual source params
        self.__source_reconnect_on_failure = True           # reconnect/restart source if fails/ends
        self.__source_imshow: bool = False                  # imshow the source frames
        self.__drop_frames_to_match_in_fps: bool = False    # drop if source fps > processing fps
                                                            # makes sure always recent frames are processed
        self.__roi: VFAIROI = VFAIROI()                     # ROI; for the time being, we are allowing one ROI

        ######################################################################################
        ############################# Target related #########################################
        ######################################################################################
        self.__target: VFAIStreamProp = VFAIStreamProp()    # target params; modified from source

        ######################################################################################
        ############################# Motion related #########################################
        ######################################################################################
        self.__motion_percent: float = 0.02            # 0.02 -> 2% of ROI area
        self.__motion_imshow_threshold: bool = False   # will show the threshold using imshow

        ######################################################################################
        ############################# Tracker related ########################################
        ######################################################################################
        self.__tracker_enable: bool = True
        self.__tracker_name: str = 'cv2_TrackerKCF'

    ######################################################################################
    ############################# Common Config ##########################################
    ######################################################################################
    @property
    def debug(self):
        return self.__c_debug
    
    @debug.setter
    def debug(self, debug: bool):
        self.__c_debug = debug

    @property
    def verbose(self):
        return self.__c_verbose
    
    @verbose.setter
    def verbose(self, verbose: bool):
        self.__c_verbose = verbose

    @property
    def dump_results(self):
        return self.__c_dump_results
    
    @dump_results.setter
    def dump_results(self, dump_results: bool):
        self.__c_dump_results = dump_results

    @property
    def results_dump_path(self):
        return self.__c_results_dump_path
    
    @results_dump_path.setter
    def results_dump_path(self, results_dump_path: str):
        self.__c_results_dump_path = results_dump_path

    ######################################################################################
    ############################# AI model/detection related #############################
    ######################################################################################
    @property
    def model(self):
        return self.__d_model_name
    
    @model.setter
    def model(self, model_name: str):
        self.__d_model_name = model_name

    @property
    def threshold(self):
        return self.__d_threshold
    
    @threshold.setter
    def threshold(self, threshold: float):
        self.__d_threshold = threshold

    @property
    def d_imshow(self):
        return self.__c_debug and self.__d_imshow
    
    @d_imshow.setter
    def d_imshow(self, d_imshow: bool):
        self.__d_imshow = d_imshow

    ######################################################################################
    ############################# Source related #########################################
    ######################################################################################
    @property
    def source(self):
        return self.__source
    
    @source.setter
    def source(self, value):
        url, height, width, fps = value
        self.__source.url = url
        self.__source.height = height
        self.__source.width = width
        self.__source.aspect_ratio = width/height
        self.__source.fps = fps

    @property
    def reconnect_source_on_failure(self) -> bool:
        return self.__source_reconnect_on_failure
    
    @reconnect_source_on_failure.setter
    def reconnect_source_on_failure(self, reconnect_source_on_failure: bool):
        self.__source_reconnect_on_failure = reconnect_source_on_failure

    @property
    def source_imshow(self):
        return self.__c_debug and self.__source_imshow
    
    @source_imshow.setter
    def source_imshow(self, source_imshow: bool):
        self.__source_imshow = source_imshow
        
    @property
    def drop_frames_to_match_in_fps(self):
        return self.__drop_frames_to_match_in_fps
    
    @drop_frames_to_match_in_fps.setter
    def drop_frames_to_match_in_fps(self, drop_frames_to_match_in_fps: bool):
        self.__drop_frames_to_match_in_fps = drop_frames_to_match_in_fps

    @property
    def roi(self):
        return self.__roi
    
    @roi.setter
    def roi(self, value):
        x1, y1, x2, y2 = value
        self.__roi.top_left = (x1, y1)
        self.__roi.bottom_right = (x2, y2)

    ######################################################################################
    ############################# Target related #########################################
    ######################################################################################
    @property
    def target(self):
        return self.__target
    
    @target.setter
    def target(self, value):
        url, height, width, fps = value
        self.__target.url = url
        self.__target.height = height
        self.__target.width = width
        self.__target.aspect_ratio = width/height
        self.__target.fps = fps

    ######################################################################################
    ############################# Motion related #########################################
    ######################################################################################
    @property
    def motion_percent(self):
        return self.__motion_percent
    
    @motion_percent.setter
    def motion_percent(self, motion_percent: float):
        self.__motion_percent = motion_percent

    @property
    def motion_imshow_threshold(self):
        return self.__c_debug and self.__motion_imshow_threshold
    
    @motion_imshow_threshold.setter
    def motion_imshow_threshold(self, motion_imshow_threshold: bool):
        self.__motion_imshow_threshold = motion_imshow_threshold

    ######################################################################################
    ############################# Tracker related ########################################
    ######################################################################################
    @property
    def enable_tracker(self):
        return self.__tracker_enable
    
    @enable_tracker.setter
    def enable_tracker(self, enable_tracker: bool):
        self.__tracker_enable = enable_tracker

    @property
    def tracker_name(self):
        return self.__tracker_name
    
    @tracker_name.setter
    def tracker_name(self, tracker_name: str):
        self.__tracker_name = tracker_name