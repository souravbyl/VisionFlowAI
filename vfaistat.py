class VFAIStat:
    def __init__(self):
        self._in = 0
        self._ok = 0
        self._err = 0
        self._invalid = 0
    
    def add_in(self):
        self._in += 1
    
    def get_in(self):
        return self._in
    
    def add_ok(self):
        self._ok += 1
    
    def get_ok(self):
        return self._ok
    
    def add_err(self):
        self._err += 1
    
    def get_err(self):
        return self._err
    
    def add_invalid(self):
        self._invalid += 1
    
    def get_invalid(self):
        return self._invalid