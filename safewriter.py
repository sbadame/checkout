
from tempfile import mkstemp
import os
import shutil

def get_tmp_filename(*args, **kwargs):
    oshandle, filename = mkstemp(*args, **kwargs)
    os.close(oshandle)
    os.remove(filename)
    return filename

class SafeWrite(object):

    def __init__(self, name, mode=''):
        self.name = name
        self.mode = mode
        self.tempfile = None
        self.write_context_manager = None
        self.read_context_manager = None

    def __enter__(self):
        oshandle, self.tempfile = mkstemp()

        self.write_context_manager = open(self.tempfile, "w"+self.mode)
        self.write_context_manager.__enter__()

        try:
            self.read_context_manager = open(self.name, "r"+self.mode)
            self.read_context_manager.__enter__()
        except IOError as ioe:
            if ioe.errno == 2:
                self.read_context_manager = None
            else:
                raise ioe

        return self.write_context_manager, self.read_context_manager

    def __exit__(self, exc_type, exc_value, traceback):
        self.write_context_manager.__exit__(exc_type, exc_value, traceback)
        if self.read_context_manager:
            self.read_context_manager.__exit__(exc_type, exc_value, traceback)

        if (exc_type, exc_value, traceback) == (None, None, None):
            backupfile = get_tmp_filename(
                suffix=".backup",
                prefix=self.name)
            try:
                shutil.copy(self.name, backupfile)
                print("Backed up: %s to %s" % (self.name, backupfile))
            except IOError as ioe:
                if ioe.errno == 2:
                    pass
                else:
                    raise ioe
            shutil.copy(self.tempfile, self.name)
