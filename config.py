import json

class Config(dict):
    def __init__(self, filepath, *args):
        self.filepath = filepath
        super(Config, self).__init__(self, *args)

    @staticmethod
    def load_from_file(fp):
        c = Config(fp.name)
        for k,v in json.load(fp).items():
            c.__setitem__withoutwrite(k, v)
        return c

    def __setitem__withoutwrite(self, key, val):
        super(Config, self).__setitem__(key, val)

    def __setitem__(self, key, val):
        super(Config, self).__setitem__(key, val)
        with open(self.filepath, "w") as configfile:
            json.dump(self, configfile)
