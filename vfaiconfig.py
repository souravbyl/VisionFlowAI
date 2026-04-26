import logging

from vfairoi import VFAIROI
from vfaistreamprop import VFAIStreamProp


class VFAIConfig:
    def __init__(self):
        self.__logger = logging.getLogger(__name__)

        ######################################################################################
        ############################# Application General Config #############################
        ######################################################################################
        self.__c_debug: bool = False  # Kill switch for overall debug level
        self.__c_loglevel: int = (
            logging.INFO
        )  # Log level: d(debug), i(info), w(warning), e(error), c(critical)

        ######################################################################################
        ############################# Display Related Config #################################
        ######################################################################################
        self.__imshow_source_frames: bool = False  # imshow the source frames
        self.__imshow_motion_threshold: bool = False  # imshow the motion threshold
        self.__imshow_motion_results: bool = False  # imshow the motion detection result
        self.__imshow_tracker_results: bool = False  # imshow the tracker result
        self.__imshow_detection_results: bool = False  # imshow the detection results

        ######################################################################################
        ############################# Event Related Config ###################################
        ######################################################################################
        self.__event_dump_path = "dumps"  # results will be dumped here

        ######################################################################################
        ############################# AI model/detection related #############################
        ######################################################################################
        self.__d_model_name: str = ""  # model name
        self.__d_threshold: float = 0.8  # minimum confidence we will allow

        ######################################################################################
        ############################# Source related #########################################
        ######################################################################################
        self.__source: VFAIStreamProp = VFAIStreamProp()  # actual source params
        self.__source_reconnect_on_failure = (
            True  # reconnect/restart source if fails/ends
        )
        self.__roi: VFAIROI = VFAIROI()  # ROI; for the time being, we are
        # allowing one ROI

        ######################################################################################
        ############################# Target related #########################################
        ######################################################################################
        self.__target: VFAIStreamProp = (
            VFAIStreamProp()
        )  # target params; modified from source

        ######################################################################################
        ############################# Motion related #########################################
        ######################################################################################
        self.__motion_percent: float = 0.02  # 0.02 -> 2% of ROI area

        ######################################################################################
        ############################# Tracker related ########################################
        ######################################################################################
        self.__tracker_enable: bool = True
        self.__tracker_name: str = "cv2_TrackerKCF"

    ######################################################################################
    ############################# Application General Config #############################
    ######################################################################################
    @property
    def debug(self):
        return self.__c_debug

    @debug.setter
    def debug(self, debug: bool):
        self.__c_debug = debug

    @property
    def loglevel(self):
        return self.__c_loglevel

    @loglevel.setter
    def loglevel(self, loglevel: str):
        if loglevel == "d":
            self.__c_loglevel = logging.DEBUG
        elif loglevel == "i":
            self.__c_loglevel = logging.INFO
        elif loglevel == "w":
            self.__c_loglevel = logging.WARN
        elif loglevel == "e":
            self.__c_loglevel = logging.ERROR
        elif loglevel == "c":
            self.__c_loglevel = logging.CRITICAL
        else:
            self.__c_loglevel = logging.INFO

    ######################################################################################
    ############################# Display Related Config #################################
    ######################################################################################

    @property
    def imshow_source_frames(self):
        return self.__c_debug and self.__imshow_source_frames

    @imshow_source_frames.setter
    def imshow_source_frames(self, imshow_source_frames: bool):
        self.__imshow_source_frames = imshow_source_frames

    @property
    def imshow_motion_threshold(self):
        return self.__c_debug and self.__imshow_motion_threshold

    @imshow_motion_threshold.setter
    def imshow_motion_threshold(self, imshow_motion_threshold: bool):
        self.__imshow_motion_threshold = imshow_motion_threshold

    @property
    def imshow_motion_results(self):
        return self.__c_debug and self.__imshow_motion_results

    @imshow_motion_results.setter
    def imshow_motion_results(self, imshow_motion_results: bool):
        self.__imshow_motion_results = imshow_motion_results

    @property
    def imshow_tracker_results(self):
        return self.__c_debug and self.__imshow_tracker_results

    @imshow_tracker_results.setter
    def imshow_tracker_results(self, imshow_tracker_results: bool):
        self.__imshow_tracker_results = imshow_tracker_results

    @property
    def imshow_detection_results(self):
        return self.__c_debug and self.__imshow_detection_results

    @imshow_detection_results.setter
    def imshow_detection_results(self, imshow_detection_results: bool):
        self.__imshow_detection_results = imshow_detection_results

    ######################################################################################
    ############################# Event Related Config ###################################
    ######################################################################################

    @property
    def event_dump_path(self):
        return self.__event_dump_path

    @event_dump_path.setter
    def event_dump_path(self, event_dump_path: str):
        self.__event_dump_path = event_dump_path

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
        self.__source.aspect_ratio = width / height
        self.__source.fps = fps

    @property
    def reconnect_source_on_failure(self) -> bool:
        return self.__source_reconnect_on_failure

    @reconnect_source_on_failure.setter
    def reconnect_source_on_failure(self, reconnect_source_on_failure: bool):
        self.__source_reconnect_on_failure = reconnect_source_on_failure

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
        self.__target.aspect_ratio = width / height
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
