from enum import Enum
from time import sleep

from PyQt5 import QtCore

import socialreaper


class QueueState(Enum):
    RUNNING = "running"
    STOPPED = "stopped"


class JobState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SAVING = "saving"
    FINISHED = "finished"


class Job():
    def __init__(self, outputPath, sourceName, sourceFunction, functionArgs, sourceKeys, job_update):
        self.iterator = eval(
            "socialreaper.{}(**{}).{}({})".format(sourceName, sourceKeys, sourceFunction, functionArgs))
        self.outputPath = outputPath
        self.sourceName = sourceName
        self.sourceFunction = sourceFunction
        self.functionArgs = functionArgs
        self.sourceKeys = sourceKeys

        self.state = JobState.QUEUED
        self.job_update = job_update
        self.data = []
        self.flat_data = []
        self.keys = set()
        self.flat_keys = set()

    def add_data(self, data):
        self.data.append(data)
        flat_data = socialreaper.tools.flatten(data)
        self.flat_data.append(flat_data)

        keys = data.keys()
        if keys != self.keys:
            self.keys.update(keys)

        flat_keys = flat_data.keys()
        if flat_keys != self.flat_keys:
            self.flat_keys.update(flat_keys)

    def inc_data(self):
        self.state = JobState.RUNNING
        try:
            value = self.iterator.__next__()
            self.add_data(value)
            self.job_update.emit(self)
            return value
        except StopIteration:
            return self.end_job()
        except socialreaper.IterError as e:
            print("Job Failed")
            print(e)
            return self.end_job()

    def end_job(self):
        # Save CSV
        self.state = JobState.SAVING
        self.job_update.emit(self)
        print("Saving job")
        socialreaper.tools.to_csv(self.flat_data, filename=self.outputPath, flat=False)
        self.state = JobState.FINISHED
        self.job_update.emit(self)
        return False

    def send_update(self):
        if self.state == JobState.RUNNING:
            if self.iterator.total % 20:
                self.job_update.emit(self)
            else:
                return

        self.job_update.emit(self)


class Queue(QtCore.QThread):
    job_update = QtCore.pyqtSignal(Job)

    job_table = QtCore.pyqtSignal(list)

    progress_bar = QtCore.pyqtSignal(int)
    progress_table = QtCore.pyqtSignal(list)

    job_complete = QtCore.pyqtSignal(str)

    def __init__(self, window):
        super().__init__()

        self.state = QueueState.STOPPED

        self.window = window
        self.jobs = []
        self.start()
        self.add_actions()

    def add_actions(self):
        self.window.queueStart.clicked.connect(self.start_queue)
        self.window.queueStop.clicked.connect(self.stop)
        self.window.queueClear.clicked.connect(self.clear)
        self.window.queueUp.clicked.connect(self.up)
        self.window.queueDown.clicked.connect(self.down)
        self.window.queueRemove.clicked.connect(self.remove)

    def start_queue(self):
        self.state = QueueState.RUNNING

    def stop(self):
        self.state = QueueState.STOPPED

    def clear(self):
        self.jobs.clear()
        self.job_table.emit(self.jobs)

    def up(self):
        pass

    def down(self):
        pass

    def remove(self):
        pass

    def add_jobs(self, details):
        try:
            for params in details:
                self.jobs.append(Job(*params, self.job_update))
        except Exception as e:
            print(f"Error occurred adding iterator\n{e}")

        self.job_table.emit(self.jobs)

    def test(self):
        print("Hello")

    def run(self):
        while True:
            if self.state == QueueState.RUNNING:
                self.inc_job()
            elif self.state == QueueState.STOPPED:
                sleep(1)

    def inc_job(self):
        if len(self.jobs) > 0:
            value = self.jobs[0].inc_data()
            # self.job_update.emit(self.jobs[0])

            if value:
                self.display_value(value)
            else:
                self.jobs.pop(0)

        else:
            self.state = QueueState.STOPPED
            self.job_table.emit(self.jobs)

    def display_value(self, value):
        print(value)


class IterateData(QtCore.QThread):
    item_generated = QtCore.pyqtSignal(dict)
    progress_changed = QtCore.pyqtSignal(int)
    api_error = QtCore.pyqtSignal(Exception)

    def __init__(self, iterator):
        super().__init__()

        self.iterator = iterator

    def run(self):
        for count, item in enumerate(self.iterator):
            print(item)