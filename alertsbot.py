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

from sps_engineering_Lib_dataQuery.confighandler import readTimeout, writeTimeout, readState, writeState, readMode

from labels import STSlabels, alertsFromMode
from myjabberbot import JabberBot, botcmd


def loadAlarmState():
    def camMode():
        modes = readMode()
        return dict([(n.split('xcu_')[1], m) for n, m in modes.items() if 'xcu_' in n])

    modes = camMode()
    states = readState()
    for cam, mode in modes.items():
        alerts = alertsFromMode[mode]
        dataIds = dict([(v, k) for k, v in STSlabels.items()])
        for alert, state in alerts:
            dataId = dataIds['%s-%s' % (cam.upper(), alert)]
            states[dataId] = state

    return states


class AlertsBot(JabberBot):
    """This is a simple broadcasting client """
    TIMEOUT_LIM = 90
    ALERT_FREQ = 60

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
    def timeout_info(self, mess, args):
        """list and states of timeout """
        timeoutAck = readTimeout()
        timeoutAck = [t for t in timeoutAck if isinstance(t, int)]

        ret = ['%d:%s   %s' % (dataId, STSlabels[dataId], 'ACK') for dataId in timeoutAck]

        return '\n' + '\n'.join(ret)

    @botcmd
    def alerts_info(self, mess, args):
        """list and states of devices that can be set in alert"""
        states = readState()
        states = dict([(k, v) for k, v in states.items() if isinstance(k, int)])

        ret = ['%d:%s   %s' % (dataId, STSlabels[dataId], bool) for dataId, bool in states.items()]

        return '\n' + '\n'.join(ret)

    @botcmd
    def timeout(self, mess, args):
        """timeout deviceName|all off|on """
        args = [arg.strip().lower() for arg in str(args).strip().split(' ') if arg]
        if len(args) != 2:
            return 'not enough arguments'

        dataId, command = (args[0], args[1]) if args[1] in ['on', 'off'] else (args[1], args[0])

        if command not in ['on', 'off']:
            return 'available args are on, off'

        timeoutAck = readTimeout()

        if dataId == 'all':
            dataId = -1
            if command == 'on':
                timeoutAck = [s for s in timeoutAck if not isinstance(s, int)]
            else:
                timeoutAck.extend(self.checkTimeout(doSend=False))
        else:
            dataId = int(dataId)
            if command == 'on':
                if dataId in timeoutAck:
                    timeoutAck.remove(dataId)
                else:
                    return '%d not in timeoutAck' % dataId
            else:
                timeoutAck.append(dataId)

        writeTimeout(list(set(timeoutAck)))
        self.sendAlertMsg(mess=mess, alertMsg="Timeout %d:%s  %s" % (dataId, STSlabels[dataId], command))

        return ''

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
            dataId = -1
            if command == 'on':
                alerts = [k for k in states.keys() if isinstance(k, int)]
                bool = True
            else:
                alerts = self.checkAlerts(doSend=False)
                bool = False

            for alert in alerts:
                states[alert] = bool
        else:
            dataId = int(dataId)
            if dataId in STSlabels.keys():
                states[dataId] = True if command == 'on' else False
            else:
                return '%d not in alert' % dataId

        writeState(states)
        self.sendAlertMsg(mess=mess, alertMsg="Alert %d:%s  %s" % (dataId, STSlabels[dataId], command))

        return ''

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.get_ping() > self.PING_FREQUENCY:
            self._idle_ping()

        if self.PING_FREQUENCY and time.time() - self.get_alert() > self.ALERT_FREQ:
            self._set_alert()
            self.checkTimeout()

        if self.PING_FREQUENCY and time.time() - self.get_awake() > self.PING_FREQUENCY / 2:
            self._send_status()
            self.checkAlerts()

    def thread_proc(self):
        pass

    def checkAlerts(self, doSend=True):
        datums = self.unPickle('/software/ait/alarm/datum.pickle')
        self.doPickle('/software/ait/alarm/datum.pickle', [])
        states = loadAlarmState()
        alerts = []
        for datum in datums:
            try:
                value, status = self.handleDatum(datum)
            except ValueError:
                continue

            state = True if datum.id not in states.keys() else states[datum.id]

            if state and status != "OK":
                alerts.append(datum.id)
                if doSend:
                    self.sendAlertMsg(alertMsg='%d : %s \n -= %s =-' % (datum.id,
                                                                        STSlabels[datum.id],
                                                                        status))
        return alerts

    def checkTimeout(self, doSend=True):
        timeoutAck = readTimeout()
        timeout = []
        for datum in self.datums.values():
            delta = time.time() - datum.timestamp

            if delta > AlertsBot.TIMEOUT_LIM and datum.id not in timeoutAck:
                timeout.append(datum.id)

                if doSend:
                    self.sendAlertMsg(alertMsg='%d : %s \n -= NO DATA since %ds =-' % (datum.id,
                                                                                       STSlabels[datum.id],
                                                                                       delta))
        return timeout

    def handleDatum(self, datum):
        self.datums[datum.id] = datum
        return datum.value

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
