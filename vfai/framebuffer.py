class FrameBuffer:
    def __init__(self):
        self._frame = None
        self._version = 0

    def write(self, frame):
        self._version += 1
        self._frame = (self._version, frame)

    def read(self, last_version):
        data = self._frame
        if data is None:
            return None, last_version

        version, frame = data
        if version == last_version:
            return None, last_version

        return frame, version
