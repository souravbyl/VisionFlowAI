from vfai.coordinate import Coordinate


class ROI:
    def __init__(self) -> None:
        self.__top_left = Coordinate()
        self.__bottom_right = Coordinate()

    @property
    def top_left(self):
        return self.__top_left

    @top_left.setter
    def top_left(self, value):
        x, y = value
        self.__top_left.xy = (x, y)

    @property
    def bottom_right(self):
        return self.__bottom_right

    @bottom_right.setter
    def bottom_right(self, value):
        x, y = value
        self.__bottom_right.xy = (x, y)

    def is_set(self):
        return self.__top_left.set and self.__bottom_right.set
