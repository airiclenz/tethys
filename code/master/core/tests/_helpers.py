class FakeTimer:
    '''Drop-in for threading.Timer that does not actually run. Records the
    scheduled interval and lets a test fire the callback synchronously.'''

    def __init__(self, interval, function, args=None, kwargs=None):
        self.interval = interval
        self.function = function
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}
        self.started = False
        self.cancelled = False
        self.daemon = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        self.function(*self.args, **self.kwargs)

    def join(self, timeout=None):
        pass
