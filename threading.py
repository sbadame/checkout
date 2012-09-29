from PyQt4 import QtCore

_asyncs = []
_progress_thread = None

def _default_progress(text):
    print("Task Progress: " + str(text))

def _no_op():
    pass

""" library for handling some threading """
def longtask(tasks,
        on_progress = _default_progress,
        on_start = _no_op,
        on_finish = _no_op,
        on_terminate = _no_op):
    global _progress_thread

    for slot, task in tasks:
        async = ASyncWorker(slot, task)
        async.progress.connect(on_progress)
        async.start()
        _asyncs.append(async)

    def wait_for_death():
        print("Waiting for all tasks to finish...")
        for async in _asyncs: async.wait()
        print("All done!")

        #Update the UI only if everything finished correctly.
        if all(async.finished for async in _asyncs):
            for async in _asyncs: async.commit()

        del _asyncs[:]

    _progress_thread = QtCore.QThread()
    _progress_thread.run = wait_for_death
    _progress_thread.started.connect(on_start)
    _progress_thread.finished.connect(on_finish)
    _progress_thread.terminated.connect(on_terminate)
    _progress_thread.start()

def cancel_longtask():
    for async in _asyncs:
        async.terminate()

class ASyncWorker(QtCore.QThread):
    signal = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, slot, task, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.task = task
        self.signal.connect(slot)
        self.finished = False
        self.result = None

    def log(self, message):
        self.progress.emit(message)
        print("[LOG] " + message)

    def run(self):
        self.result = self.task(self.log)
        self.finished = True

    def commit(self):
        if self.finished:
            if not self.result:
                self.result = ""
            self.signal.emit(self.result)
