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

import collections
import logging
import time
from datetime import datetime as dt

from sps_engineering_JabberBot.jabberbot import JabberBot, botcmd
from sps_engineering_JabberBot.utils import loadSTSHelp, inAlert, loadDatums, AlertBuffer, readState, writeState, \
    getUserAlert, setUserAlert


class AlertsBot(JabberBot):
    """This is a simple broadcasting client """
    ALERT_FREQ = 30

    def __init__(self, jid, password):
        self.datums = {}
        self.stsHelp = loadSTSHelp()
        self.log = logging.getLogger('JabberBot.AlertsBot')
        self.alertBuffer = AlertBuffer()
        self.thread_killed = False

        JabberBot.__init__(self, jid, password)

        self._getCommand()

    @botcmd
    def alert_mode(self, mess, args):
        """Be noticed by the alarms args : on/off"""
        userAlert = getUserAlert()

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
            setUserAlert(userAlert)
            return msg
        else:
            return 'unknown args'

    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list

    @botcmd
    def alert_msg(self, mess, args):
        """Sends out a broadcast to users on ALERT, supply message as arguments (e.g. broadcast hello)"""
        self.broadcastAlert(mess=mess, alertMsg=args)

    @botcmd(hidden=True)
    def kill(self, mess, args):
        self.shutdown()

    @botcmd
    def alerts_info(self, mess, args):
        """list and states of devices that can be set in alert"""
        states = readState()
        states = collections.OrderedDict(sorted([(k, v) for k, v in states.items() if isinstance(k, int)]))

        ret = [' %d, %s = %s' % (dataId, self.stsHelp[dataId], bool) for dataId, bool in states.items()]

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
                dataIds = self.alertBuffer.current.keys()
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
        self.broadcastAlert(mess=mess,
                            alertMsg='\n'.join(
                                ['%d, %s = %s' % (dataId, self.stsHelp[dataId], command) for dataId in dataIds]))

        return ''

    @botcmd
    def summary(self, mess, args):
        """return latest telemetry values."""
        sortedByStsIds = collections.OrderedDict(sorted(self.datums.items()))
        allMsg = [self.datumToMsg(datum, includeValue=True) for datum in sortedByStsIds.values()]
        return '\n' + '\r\n'.join(allMsg)

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.get_ping() > self.PING_FREQUENCY:
            self._idle_ping()
            self._send_status()
            self.handleAlerts()

    def thread_proc(self):
        pass

    def datumToMsg(self, datum, includeValue=False):
        value, status = datum.value
        header = '-=%d, %s =-' % (datum.id, self.stsHelp[datum.id])
        timestamp = str(dt.fromtimestamp(datum.timestamp))
        toJoin = [timestamp, '%g' % value, status] if includeValue else [timestamp, status]
        text = '   '.join(toJoin)
        msg = '\n'.join([header, text])
        return msg

    def handleAlerts(self):
        self.checkAlerts()
        toSend = self.alertBuffer.filterTraffic()
        sortedByStsIds = collections.OrderedDict(sorted([(datum.id, datum) for datum in toSend]))

        for datum in sortedByStsIds.values():
            alertMsg = self.datumToMsg(datum)
            self.sendAlert(alertMsg=alertMsg)

        self.alertBuffer.clear()

    def checkAlerts(self):
        doWrite = False
        datums = self.retrieveDatums()
        states = readState()

        for datum in datums:
            try:
                value, status = datum.value
            except ValueError:
                continue

            if datum.id not in states.keys():
                states[datum.id] = True
                doWrite = True

            state = states[datum.id]

            if state and status != "OK":
                self.alertBuffer.append(datum)

        if doWrite:
            writeState(states)

    def broadcastAlert(self, mess, alertMsg):
        header = '%s %s:' % (str(mess.getFrom().getNode()), dt.fromtimestamp(time.time()))
        self.sendAlert('\n'.join([header, alertMsg]))

    def sendAlert(self, alertMsg):
        userAlert = getUserAlert()
        self.log.debug(alertMsg)

        for jid in userAlert.values():
            self.send(jid, alertMsg)

    def updateJID(self, jid):
        userAlert = getUserAlert()
        user = jid.getNode()
        self.log.info('updating jid : %s for user %s' % (jid, user))
        if user in userAlert.iterkeys() and userAlert[user] != jid:
            userAlert[user] = jid
            setUserAlert(userAlert)

    def retrieveDatums(self):
        datums = loadDatums()

        for datum in datums:
            if datum.id in self.datums.keys() and (inAlert(self.datums[datum.id]) and not inAlert(datum)):
                continue

            self.datums[datum.id] = datum

        return self.datums.values()
