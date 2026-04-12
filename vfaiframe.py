class VFAIFrame:
    def __init__(self, data=None, since_start=None, epoch=None, metadata={}) -> None:
        self._data = data
        self._since_start = since_start
        self._epoch = epoch
        self._metadata = metadata