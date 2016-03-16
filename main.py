import sys, os

absolute_path = os.getcwd() + '/' + sys.argv[0].split('main.py')[0]
sys.path.insert(0, absolute_path.split('Engineering_JabberBot')[0])
addr = sys.argv[1] if len(sys.argv) > 1 else "localhost"
port = sys.argv[2] if len(sys.argv) > 2 else 5432
from broadcast import JabberBotManager

# Fill in the JID + Password of your JabberBot here...
(JID, PASSWORD) = ('pfs@jappix.com', 'xmpp4pfs')

JabberBotManager(absolute_path, addr, port, JID, PASSWORD)
