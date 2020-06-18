""" Create a new thread where a function will be called periodically """

# Author: Roberto Buelvas

from threading import Timer


class RepeatedTimer(object):
    """ Class to create new thread """

    def __init__(self, interval, function, *args, **kwargs):
        """ Create new object """
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def start(self):
        """ Attach a timer if there is none already """
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def _run(self):
        """ Call function when timer runs up """
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def stop(self):
        """ Unattach timer """
        self._timer.cancel()
        self.is_running = False
