from __future__ import annotations


class VFAIStreamProp:
    def __init__(self, other: VFAIStreamProp | None = None) -> None:
        self.__url: str = ""
        self.__height: int = 0
        self.__width: int = 0
        self.__aspect_ratio: float = 0.0
        self.__fps: int = 0
        if other is not None:
            self.__url: str = other.url
            self.__height: int = other.height
            self.__width: int = other.width
            self.__aspect_ratio: float = other.aspect_ratio
            self.__fps: int = other.fps

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, url: str):
        if url is None or len(url) == 0:
            raise ValueError(f"Invalid url {url}!")
        self.__url = url

    @property
    def height(self):
        return self.__height

    @height.setter
    def height(self, height: int):
        if height <= 0:
            raise ValueError(f"Invalid height {height}!")
        self.__height = height

    @property
    def width(self) -> int:
        return self.__width

    @width.setter
    def width(self, width: int):
        if width <= 0:
            raise ValueError(f"Invalid width {width}!")
        self.__width = width

    @property
    def aspect_ratio(self) -> float:
        return self.__aspect_ratio

    @aspect_ratio.setter
    def aspect_ratio(self, aspect_ratio: float):
        if aspect_ratio <= 0:
            raise ValueError(f"Invalid aspect_ratio {aspect_ratio}!")
        self.__aspect_ratio = aspect_ratio

    @property
    def fps(self) -> int:
        return self.__fps

    @fps.setter
    def fps(self, fps: int):
        if fps <= 0:
            raise ValueError(f"Invalid fps {fps}!")
        self.__fps = fps
