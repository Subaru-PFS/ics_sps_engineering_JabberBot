#!/usr/bin/python

# JabberBot: A simple jabber/xmpp bot framework
# Copyright (c) 2007-2011 Thomas Perl <thp.io/about>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import pickle
import random
import time
from datetime import datetime as dt
from sps_engineering_Lib_dataQuery.confighandler import readState, writeState

from sps_engineering_JabberBot.jabberbot import JabberBot, botcmd


class AlertsBot(JabberBot):
    """This is a simple broadcasting client """
    TIMEOUT_LIM = 150
    ALERT_FREQ = 30
    TIMEOUT_FREQ = 60

    def __init__(self, jid, password):
        self.datums = {}
        self.log = logging.getLogger('JabberBot.AlertsBot')
        self.thread_killed = False

        JabberBot.__init__(self, jid, password)

        self._getCommand()

    @botcmd
    def alert_mode(self, mess, args):
        """Be noticed by the alarms args : on/off"""
        userAlert = self.unPickle("userAlarm")

        args = str(args)
        if args in ['on', 'off']:
            user = mess.getFrom().getNode()
            if args.strip() == 'on':
                if user not in userAlert.iterkeys():
                    userAlert[user] = mess.getFrom()
                    msg = "You are on alert MODE !"
                else:
                    msg = "You already are on alert mode \n Stop wasting my time please !"
            else:
                if user in userAlert.iterkeys():
                    userAlert.pop(user, None)
                    msg = "You aren't on alert MODE anymore !"
                else:
                    msg = "Are you kidding me !?"
            self.doPickle('userAlarm', userAlert)
            return msg
        else:
            return 'unknown args'

    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list

    @botcmd
    def alert_msg(self, mess, args):
        """Sends out a broadcast to users on ALERT, supply message as arguments (e.g. broadcast hello)"""
        self.sendAlertMsg(mess=mess, alertMsg='broadcast: %s' % args)

    @botcmd(hidden=True)
    def kill(self, mess, args):
        self.shutdown()

    @botcmd
    def alerts_info(self, mess, args):
        """list and states of devices that can be set in alert"""
        states = readState()
        states = dict([(k, v) for k, v in states.items() if isinstance(k, int)])

        ret = [' dataId : %d = %s' % (dataId, bool) for dataId, bool in states.items()]

        return '\n' + '\n'.join(ret)

    @botcmd
    def alerts(self, mess, args):
        """timeout deviceName|all off|on """
        args = [arg.strip().lower() for arg in str(args).strip().split(' ') if arg]
        if len(args) != 2:
            return 'not enough arguments'

        dataId, command = (args[0], args[1]) if args[1] in ['on', 'off', 'ack'] else (args[1], args[0])

        if command not in ['on', 'off', 'ack']:
            return 'available args are on, off, ack'

        states = readState()

        if dataId == 'all':
            if command == 'on':
                dataIds = [k for k in states.keys() if isinstance(k, int)]
            else:
                dataIds = self.checkAlerts(doSend=False)
        else:
            try:
                dataIds = [int(dataId)]
            except ValueError:
                return 'invalid STS dataID'

        for dataId in dataIds:
            if dataId not in states.keys():
                return 'dataId : %d not in alert' % dataId

            if command == 'on':
                self.datums.pop(dataId, None)
                states[dataId] = True
            elif command == 'off':
                states[dataId] = False
            else:
                self.datums.pop(dataId, None)

        writeState(states)
        self.sendAlertMsg(mess=mess, alertMsg="Alert dataId : %d  %s" % (dataId, command))

        return ''

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.get_ping() > self.PING_FREQUENCY:
            self._idle_ping()

        if self.PING_FREQUENCY and time.time() - self.get_alert() > self.ALERT_FREQ:
            self._set_alert()
            self.checkAlerts()

        if self.PING_FREQUENCY and time.time() - self.get_awake() > 5:
            self._send_status()

    def thread_proc(self):
        pass

    def checkAlerts(self, doSend=True):
        datums = self.loadDatums()
        states = readState()

        alerts = []
        for datum in datums:
            try:
                value, status = datum.value
            except ValueError:
                continue

            if datum.id not in states.keys():
                states[datum.id] = True
                writeState(states)

            state = states[datum.id]

            if state and status != "OK":
                alerts.append(datum.id)
                if doSend:
                    self.sendAlertMsg(alertMsg='dataId : %d \n -= %s =-' % (datum.id,
                                                                            status))
        return alerts

    def sendAlertMsg(self, mess=False, alertMsg=''):
        userAlert = self.unPickle("userAlarm")

        for m in alertMsg.split('\r\n'):
            self.log.debug(m)

        alertMsg += ("  by %s  on %s" % (str(mess.getFrom().getNode()), dt.now().isoformat()[:19]) if mess else '')

        for jid in userAlert.values():
            self.send(jid, alertMsg)

    def updateJID(self, jid):
        userAlert = self.unPickle("userAlarm")
        user = jid.getNode()
        self.log.info('updating jid : %s for user %s' % (jid, user))
        if user in userAlert.iterkeys() and userAlert[user] != jid:
            userAlert[user] = jid
            self.doPickle('userAlert', userAlert)

    def loadDatums(self):
        datums = self.unPickle('/home/arnaud/software/ait/alarm/datum.pickle')
        self.doPickle('/home/arnaud/software/ait/alarm/datum.pickle', [])

        for datum in sorted(datums, key=lambda x: x.timestamp):
            if datum.id in dicta.keys() and (self.inAlert(dicta[datum.id]) and not self.inAlert(datum)):
                continue

            self.datums[datum.id] = datum

        return self.datums.values()

    def inAlert(self, datum):
        value, status = datum.value
        return status != 'OK'

    def unPickle(self, filepath):
        try:
            with open(filepath, 'rb') as thisFile:
                unpickler = pickle.Unpickler(thisFile)
                return unpickler.load()
        except EOFError:
            time.sleep(0.1 + random.random())
            return self.unPickle(filepath=filepath)

    def doPickle(self, filepath, var):
        with open(filepath, 'wb') as thisFile:
            pickler = pickle.Pickler(thisFile, protocol=2)
            pickler.dump(var)
