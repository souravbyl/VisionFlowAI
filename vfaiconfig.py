class VFAIConfig:
    def __init__(self):
        self._threshold = 0.8
        self._model = None
        self._verbose = False
        
        self._source = None
        self._target_width = 0
        self._target_height = 0
        self._target_fps = 0
    
    def get_threshold(self):
        return self._threshold
    
    def get_model(self):
        return self._model
    
    def get_verbosity(self):
        return self._verbose
    
    def get_source(self):
        return self._source
    
    def _get_target_width(self):
        return self._target_width
    
    def _get_target_height(self):
        return self._target_height
    
    def _get_target_fps(self):
        return self._target_fps