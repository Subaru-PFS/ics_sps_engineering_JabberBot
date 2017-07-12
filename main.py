import logging
import os
import sys
import threading
import time
from datetime import datetime as dt

from mythread import pingXmpp

absPath = os.getcwd() + '/' + sys.argv[0].split('main.py')[0]
sys.path.insert(0, absPath.split('ics_sps_engineering_JabberBot')[0])

from pfsbot import PfsBot

# create logger with 'spam_application'
logger = logging.getLogger('JabberBot')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('/home/pfs/AIT-PFS/jabberLog/%s.log' % dt.now().strftime("%Y-%m-%d_%H-%M"))
#fh = logging.FileHandler('/home/alefur/AIT-PFS/jabberLog/%s.log' % dt.now().strftime("%Y-%m-%d_%H-%M"))
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

addr = sys.argv[1] if len(sys.argv) > 1 else "localhost"
port = sys.argv[2] if len(sys.argv) > 2 else 5432

# Fill in the JID + Password of your JabberBot here...
(JID, PASSWORD) = ('pfs@lam.fr', 'xmpp4pfs')

try:
    while True:
        time.sleep(2)
        if pingXmpp("xmpp.osupytheas.fr"):
            logger.debug("Creating an instance of PfsBot")
            bc = PfsBot(JID, PASSWORD, absPath, addr, port)
            th = threading.Thread(target=bc.thread_proc)
            bc.serve_forever(connect_callback=lambda: th.start())
            bc.thread_killed = True
            logger.debug("PfsBot has finished")
        else:
            logger.debug("Failed to ping xmpp.osupytheas.fr")
            time.sleep(10)
except KeyboardInterrupt:
    print 'interrupted!'
