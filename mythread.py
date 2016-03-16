import threading
import datetime as dt


class StoppableThread(threading.Thread):
    def __init__(self, bot):
        """ constructor, setting initial variables """
        self._sleepperiod = 60.0
        self._stopevent = threading.Event()
        self.bot = bot
        threading.Thread.__init__(self)

    def run(self):
        """ main control loop """
        while not self._stopevent.isSet():
            self.bot.thread_proc()
            self._stopevent.wait(self._sleepperiod)
        else:
            print "%s   Thread finished" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def join(self, timeout=None):
        """ Stop the thread and wait for it to end. """
        self._stopevent.set()
        threading.Thread.join(self, timeout)
