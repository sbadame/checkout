
from tempfile import mkstemp

class WriteSafelyManager(object):

    def __init__(self, name, mode):
        self.name = name
        self.mode = mode

    def __enter__(self):
        self.tempfile = mkstemp()
        return self.tempfile

    def __exit__(self, exc_type, exc_value, traceback):
        if not (exc_type, exc_value, traceback) == (None, None, None):
            
