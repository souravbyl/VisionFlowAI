class VFAICoordinate:
    def __init__(self, x: int=0, y: int=0) -> None:
        self.__x: int = x
        self.__y: int = y
        self.__set: bool = False

    @property 
    def xy(self):
        return self.__x, self.__y
    
    @xy.setter
    def xy(self, value):
        x, y = value
        self.__x = x
        self.__y = y
        self.__set = True
    
    @property
    def set(self):
        return self.__set
    
    
