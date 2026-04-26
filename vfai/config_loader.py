import yaml

from vfai.config import Config


def load_config(path: str) -> Config:
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    cfg = Config()

    # app
    cfg.debug = data["app"]["debug"]
    ll = data["app"]["loglevel"]
    assert ll in ["d", "i", "w", "e", "c"]
    cfg.loglevel = ll

    # display
    cfg.imshow_source_frames = data["display"]["imshow_source_frames"]
    cfg.imshow_motion_threshold = data["display"]["imshow_motion_threshold"]
    cfg.imshow_motion_results = data["display"]["imshow_motion_results"]
    cfg.imshow_tracker_results = data["display"]["imshow_tracker_results"]
    cfg.imshow_detection_results = data["display"]["imshow_detection_results"]

    # event dump path
    cfg.event_dump_path = data["event"]["dump_path"]

    # model
    cfg.model = data["model"]["name"]
    cfg.threshold = data["model"]["threshold"]

    # source
    cfg.source.url = data["source"]["url"]
    cfg.reconnect_source_on_failure = data["source"]["reconnect_on_failure"]
    # source roi
    if data["source"]["roi"]["enabled"]:
        cfg.roi = (
            data["source"]["roi"]["x1"],
            data["source"]["roi"]["y1"],
            data["source"]["roi"]["x2"],
            data["source"]["roi"]["y2"],
        )

    # motion
    cfg.motion_percent = data["motion"]["percent"]

    # tracker
    cfg.enable_tracker = data["tracker"]["enabled"]
    cfg.tracker_name = data["tracker"]["name"]

    return cfg
