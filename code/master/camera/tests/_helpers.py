class FakeTimer:
    '''Drop-in for threading.Timer that does not actually run. Records the
    scheduled interval and the callback args (the auto-off "reason"), and lets a
    test fire the callback synchronously. Mirrors core/tests/_helpers.py.'''

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


def collecting_timer_factory():
    '''Return (factory, timers): a timer_factory that builds non-running
    FakeTimers and appends each to the returned list, so a test can find and fire
    a specific timer by its "reason" arg.'''
    timers = []

    def factory(interval, function, args=None, kwargs=None):
        timer = FakeTimer(interval, function, args, kwargs)
        timers.append(timer)
        return timer

    return factory, timers
