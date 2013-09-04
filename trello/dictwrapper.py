class DictWrapper(object):
    _data = None

    def __init__(self, data):
        self._data = data

    def __getattr__(self, attr):
        return self._data[attr]

    def __setattr__(self, attr, val):
        if self._data:
            self._data[attr] = val
        else:
            object.__setattr__(self, attr, val)
