import logging
import time
from datetime import datetime as dt

from sps_engineering_JabberBot.alertsbot import AlertsBot
from sps_engineering_JabberBot.thread import pingXmpp


def runBot(args):
    logFolder = args.logFolder

    # create logger with 'spam_application'
    logger = logging.getLogger('JabberBot')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('%s/%s.log' % (logFolder, dt.now().strftime("%Y-%m-%d_%H-%M")))

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

    # Fill in the JID + Password of your AlertsBot here...
    (JID, PASSWORD) = ('pfs-r0@lam.fr', 'xmpp4pfs')

    try:
        while True:
            time.sleep(2)
            if pingXmpp("xmpp.osupytheas.fr"):
                logger.debug("Creating an instance of AlertsBot")
                bc = AlertsBot(JID, PASSWORD)
                bc.serve_forever()
                logger.debug("AlertsBot has finished")
            else:
                logger.debug("Failed to ping xmpp.osupytheas.fr")
                time.sleep(10)
    except KeyboardInterrupt:
        print('interrupted!')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--logFolder', default='/software/ait/logs/alertsBot', type=str, nargs='?', help='log')
    args = parser.parse_args()

    runBot(args)


if __name__ == '__main__':
    main()
