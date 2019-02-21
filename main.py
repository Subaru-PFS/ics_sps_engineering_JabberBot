import logging
import threading
import time
from datetime import datetime as dt

from mythread import pingXmpp
from pfsbot import PfsBot


def runBot(args):
    cam = args.cam
    actorList = args.ait.split(',')
    logFolder = args.logFolder

    # create logger with 'spam_application'
    actorList.extend([('xcu_%s' % cam),
                      ('ccd_%s' % cam)])
    logger = logging.getLogger('JabberBot')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('%s/%s-%s.log' % (logFolder, dt.now().strftime("%Y-%m-%d_%H-%M"), cam))

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

    # Fill in the JID + Password of your JabberBot here...
    (JID, PASSWORD) = ('pfs-%s@lam.fr' % cam, 'xmpp4pfs')

    try:
        while True:
            time.sleep(2)
            if pingXmpp("xmpp.osupytheas.fr"):
                logger.debug("Creating an instance of PfsBot")
                bc = PfsBot(JID, PASSWORD, logFolder, actorList,
                            dbHost=args.host, dbPort=args.port, dbPass=args.password)
                th = threading.Thread(target=bc.thread_proc)
                bc.serve_forever(connect_callback=lambda: th.start())
                bc.thread_killed = True
                logger.debug("PfsBot has finished")
            else:
                logger.debug("Failed to ping xmpp.osupytheas.fr")
                time.sleep(10)
    except KeyboardInterrupt:
        print('interrupted!')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cam', default=None, type=str, nargs='?', help='camera name')
    parser.add_argument('--ait', default=None, type=str, nargs='?', help='ait actors list')
    parser.add_argument('--host', default='localhost', type=str, nargs='?', help='database server ip address')
    parser.add_argument('--port', default='5432', type=int, nargs='?', help='database server port')
    parser.add_argument('--password', default='', type=str, nargs='?', help='database server password')
    parser.add_argument('--logFolder', default='/software/ait/logs/jabberbot', type=str, nargs='?', help='log')

    args = parser.parse_args()

    runBot(args)


if __name__ == '__main__':
    main()
