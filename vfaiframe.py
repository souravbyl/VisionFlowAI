class VFAIFrame:
    def __init__(self, id=0, data=None, since_start=None, epoch=None, metadata={}) -> None:
        self._id = id
        self._data = data
        self._since_start = since_start
        self._epoch = epoch
        self._metadata = metadata