from queue import Queue
from threading import Lock


class Task:
    def __init__(self, bundle):
        self.tryCount = 0
        self.bundle = bundle


class StreamLine:
    EOQ = 'End of queue'

    def __init__(self, name, pending_length):
        self.workerCount = 0
        self.name = name
        self.failedQueue = Queue()
        self.__lock = Lock()
        if pending_length > 0:
            self.pendingQueue = Queue(pending_length)
        else:
            self.pendingQueue = Queue()
        self.errorList = []

    def take(self):
        with self.__lock:
            while len(self.errorList) > 0:
                task = self.errorList.pop()
                if task.tryCount >= 10:
                    self.failedQueue.put(task.bundle)
                else:
                    return task

        task = self.pendingQueue.get()
        if task is StreamLine.EOQ:
            self.pendingQueue.put(task)
        return task

    def put_error(self, task):
        with self.__lock:
            task.tryCount += 1
            self.errorList.append(task)

    def put_failed(self, task):
        self.failedQueue.put(task)

    def put(self, bundle):
        self.pendingQueue.put(Task(bundle))

    def mark_end(self):
        self.pendingQueue.put(StreamLine.EOQ)

    def get_queue_size(self):
        return self.pendingQueue.qsize()

    def __enter__(self):
        with self.__lock:
            self.workerCount += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.__lock:
            self.workerCount -= 1


class StreamLinePool:
    def __init__(self):
        self.__streamLines = {}

    def add_task(self, name, task):
        stream_line = self.get_stream_line(name)
        stream_line.pendingQueue.put(task)

    def stop_stream_line(self, name):
        stream_line = self.get_stream_line(name)
        stream_line.pendingQueue.put(StreamLine.EOQ)

    def add_stream_line(self, name, queue_size=0):
        self.__streamLines[name] = StreamLine(name, queue_size)

    def get_stream_line(self, name):
        return self.__streamLines.get(name)

    def print_status(self, log):
        msg = ""
        for line in self.__streamLines.values():
            msg += line.name + " %s/%s/%s. " % (line.workerCount, line.pendingQueue.qsize(), line.failedQueue.qsize())
        log.info(msg)
