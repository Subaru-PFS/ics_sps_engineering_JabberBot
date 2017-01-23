import os
import sys
import threading
import time
from datetime import datetime as dt

from mythread import pingXmpp

absPath = os.getcwd() + '/' + sys.argv[0].split('main.py')[0]

import logging

logging.basicConfig(filename='%s/log/%s.log' % (absPath, dt.now().strftime("%Y-%m-%d_%H-%M")), level=logging.DEBUG)

sys.path.insert(0, absPath.split('ics_sps_engineering_JabberBot')[0])
addr = sys.argv[1] if len(sys.argv) > 1 else "localhost"
port = sys.argv[2] if len(sys.argv) > 2 else 5432

# Fill in the JID + Password of your JabberBot here...
(JID, PASSWORD) = ('pfs@lam.fr', 'xmpp4pfs')

from broadcast2 import PfsJabberBot

# create console handler
chandler = logging.StreamHandler()
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to handler

chandler.setFormatter(formatter)

try:
    while True:
        time.sleep(2)
        if pingXmpp("xmpp.osupytheas.fr"):
            bc = PfsJabberBot(chandler, JID, PASSWORD, absPath, addr, port)
            th = threading.Thread(target=bc.thread_proc)
            bc.serve_forever(connect_callback=lambda: th.start())
            bc.thread_killed = True
            logging.debug("%s PfsJabberBot Over" % dt.now().strftime("%Y-%m-%d_%H-%M"))
        else:
            logging.debug("%s Failed to ping xmpp.osupytheas.fr" % dt.now().strftime("%Y-%m-%d_%H-%M"))
            time.sleep(10)
except KeyboardInterrupt:
    print 'interrupted!'
