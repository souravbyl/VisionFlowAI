import logging


class VFAIQueue:
    def __init__(self, size):
        self.size = size
        self.queue = [None] * self.size
        self.rear = self.front = -1
        self.__logger = logging.getLogger(__name__)

    def enqueue(self, element):
        if self.front == (self.rear + 1) % self.size:
            self.__logger.fatal("Queue is full, might lead to drop.")
            return None
        if self.front == -1:
            self.front = 0
        self.rear = (self.rear + 1) % self.size
        self.queue[self.rear] = element

    def dequeue(self):
        if self.front == -1:
            return None
        element = self.queue[self.front]
        self.queue[self.front] = None
        if self.front == self.rear:
            self.front = self.rear = -1
        else:
            self.front = (self.front + 1) % self.size
        return element
