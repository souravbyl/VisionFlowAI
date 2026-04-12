class VFAIQueue:
    def __init__(self, size):
        self.size = size
        self.queue = [None] * self.size
        self.rear = self.front = -1

    def enqueue(self, element):
        if self.front == (self.rear + 1) % self.size:
            print('Queue is full')
            return None
        if self.front == -1:
            self.front = 0
        self.rear = (self.rear+1) % self.size
        self.queue[self.rear] = element
    
    def dequeue(self):
        if self.front == -1:
            # print('Queue is empty')
            return None
        element = self.queue[self.front]
        self.queue[self.front] = None
        if self.front == self.rear:
            self.front = self.rear = -1
        else:
            self.front = (self.front+1) % self.size
        return element
    
    # Function to display the elements of the queue
    def displayQueue(self):
        if self.front == -1:
            print("Queue is Empty")
            return
        print("Elements in the Circular Queue are: ")
        if self.rear >= self.front:
            for i in range(self.front, self.rear + 1):
                print(self.queue[i], end=" ")
        else:
            for i in range(self.front, self.size):
                print(self.queue[i], end=" ")
            for i in range(0, self.rear + 1):
                print(self.queue[i], end=" ")
        print()