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
import os
import pickle
import random
import time
import types
from collections import OrderedDict
from datetime import datetime as dt
from datetime import timedelta

import sps_engineering_Lib_dataQuery as dataQuery
from sps_engineering_Lib_dataQuery.confighandler import loadConf, loadAlarm, readTimeout, readState, readMode, \
    writeTimeout, writeState, writeMode
from sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager

from dataset import Dataset
from myjabberbot import JabberBot, botcmd
from report import Report


class AlarmHandler(object):
    timelim = 90

    def __init__(self, pfsbot):
        self.message = {}
        self.pfsbot = pfsbot

    @property
    def alarms(self):
        return self.pfsbot.loadAlarm()

    def checkValues(self):
        state = readState()
        for alarm in self.alarms:
            if not state[alarm.label.lower()]:
                continue

            try:
                df = self.pfsbot.db.last(alarm.tablename, alarm.key)
                val = df[alarm.key]
                if not (float(alarm.lbound) <= val < float(alarm.ubound)):
                    raise Warning('OUT OF RANGE =- \n %s <= %g < %s' % (alarm.lbound,
                                                                        val,
                                                                        alarm.ubound))

            except Exception as e:
                self.message[alarm.label.lower()] = '%s \n -= ALARM %s %s' % (dt.utcnow().isoformat()[:-10],
                                                                              alarm.label,
                                                                              str(e))

        for mess in self.message.values():
            self.pfsbot.sendAlarmMsg(alarmMsg=mess)

    def clear(self, key):
        self.message.pop(key, None)


class TimeoutHandler(object):
    timelim = 90

    def __init__(self, pfsbot):
        self.pfsbot = pfsbot

        self.last_date = {}
        self.last_time = {}
        self.ping(start=True)

    @property
    def devices(self):
        return [device.tablename for device in self.pfsbot.functionList]

    @property
    def timeout_ack(self):
        return readTimeout()

    def ping(self, start=False):
        ontimeout = []
        for device in self.devices:
            try:
                df = self.pfsbot.db.last(table=device)
                tai = df['tai']
            except ValueError:
                tai = False

            if start:
                self.last_time[device] = time.time()
                self.last_date[device] = tai
            else:
                if self.checkDevice(table=device, tai=tai):
                    ontimeout.append(device)

        return ontimeout

    def checkDevice(self, table, tai):
        ontimeout = False

        if tai != self.last_date[table]:
            self.last_time[table] = time.time()
            self.last_date[table] = tai

        else:
            if table not in self.timeout_ack and ((time.time() - self.last_time[table]) > TimeoutHandler.timelim):
                self.pfsbot.sendAlarmMsg(alarmMsg="TIME OUT ON %s ! ! !" % table)
                ontimeout = True

        return ontimeout


class PfsBot(JabberBot):
    """This is a simple broadcasting client """
    TIMEOUT_LIM = 90
    ALERT_FREQ = 60

    def __init__(self, jid, password, logFolder, addr, port, actorList):
        self.log = logging.getLogger('JabberBot.PfsBot')

        self.logFolder = logFolder
        self.db_addr = addr
        self.db_port = port
        self.actorList = actorList
        self.thread_killed = False
        self.ontimeout = []

        self.db = DatabaseManager(ip=addr, port=port)
        self.db.init()

        self.functionList = self.loadConfig()
        self.timeoutHandler = TimeoutHandler(pfsbot=self)
        self.alarmHandler = AlarmHandler(pfsbot=self)
        self.loadFunctions()

        JabberBot.__init__(self, jid, password)

        self._getCommand()

    @property
    def cam(self):
        return self.actorList[-1].split('__')[-1].split('_')[-1]

    @botcmd
    def alarm_mode(self, mess, args):
        """Be noticed by the alarms args : on/off"""
        userAlarm = self.unPickle("userAlarm")

        args = str(args)
        if args in ['on', 'off']:
            user = mess.getFrom().getNode()
            if args.strip() == 'on':
                if user not in userAlarm.iterkeys():
                    userAlarm[user] = mess.getFrom()
                    msg = "You are on Alarm MODE !"
                else:
                    msg = "You already are on Alarm mode \n Stop wasting my time please !"
            else:
                if user in userAlarm.iterkeys():
                    userAlarm.pop(user, None)
                    msg = "You aren't on alarm MODE anymore !"
                else:
                    msg = "Are you kidding me !?"
            self.doPickle('userAlarm', userAlarm)
            return msg
        else:
            return 'unknown args'

    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list

    @botcmd
    def alarm_msg(self, mess, args):
        """Sends out a broadcast to users on ALARM, supply message as arguments (e.g. broadcast hello)"""
        self.sendAlarmMsg(mess=mess, alarmMsg='broadcast: %s' % args)

    @botcmd
    def alarm(self, mess, args):
        """alarm deviceName ack|off|on """
        args = str(args)
        alarmState = readState()

        if len(args.split(' ')) != 2:
            return 'not enough arguments'

        device = args.split(' ')[0].strip().lower()
        command = args.split(' ')[1].strip().lower()

        if device in ['on', 'off', 'ack']:
            device, command = command, device

        if '%s-%s' % (device, self.cam) in alarmState.iterkeys():
            device = '%s-%s' % (device, self.cam)

        if device not in alarmState.iterkeys():
            existingAlarms = list(alarmState.iterkeys())
            existingAlarms.sort()
            return '%s is not a valid device (%s)' % (device, ','.join(existingAlarms))

        if command not in ['on', 'off', 'ack']:
            return '%s is not a valid argument (on, off, ack)' % command

        if command == 'on':
            alarmState[device] = True
        elif command == 'off':
            alarmState[device] = False
            self.alarmHandler.clear(device)
        else:
            self.alarmHandler.clear(device)

        writeState(alarmState)
        self.sendAlarmMsg(mess=mess, alarmMsg="Alarm %s %s" % (device, command))

        return ''

    @botcmd
    def timeout(self, mess, args):
        """timeout deviceName|all ack|rearm """

        args = str(args)
        if len(args.split(' ')) != 2:
            return 'Not enough arguments'

        device = args.split(' ')[0].strip().lower()
        command = args.split(' ')[1].strip().lower()

        if device in ['rearm', 'ack']:
            device, command = command, device

        if command not in ['rearm', 'ack']:
            return 'available args are rearm, ack'

        timeoutAck = readTimeout()
        timeoutAck.sort()

        if device == 'all':
            allDevices = self.timeoutHandler.devices
            if command == 'rearm':
                timeoutAck = [timeout for timeout in timeoutAck if timeout not in allDevices]
            elif command == 'ack':
                timeoutAck += self.ontimeout
        else:
            if command == 'rearm':
                if device in timeoutAck:
                    timeoutAck.remove(device)
                else:
                    return '%s not in timeoutAck : %s' % (device, ','.join(timeoutAck))
            elif command == 'ack':
                timeoutAck.append(device)

        timeoutAck = list(OrderedDict.fromkeys(timeoutAck))
        writeTimeout(timeoutAck)
        self.sendAlarmMsg(mess=mess, alarmMsg="Timeout %s  %s" % (device, command))

        return ''

    @botcmd
    def all(self, mess, args):
        """Get all parameters """
        user = mess.getFrom()
        res = ""
        for attr in ['pressure', 'frontpressure', 'lam_pressure', 'ionpump1', 'ionpump2',
                     'cooler', 'temperature', 'ccdtemps', 'lamtemps1', 'lamtemps2']:

            try:
                func = getattr(self, attr)
                res += "\n%s\n" % func(mess, args)
            except:
                pass

        return res

    @botcmd
    def record(self, mess, args):
        knownUsers = self.unPickle("knownUsers")

        user = mess.getFrom().getNode()
        knownUsers[user] = args.strip()
        self.doPickle('knownUsers', knownUsers)
        return "Thanks ! "

    @botcmd
    def mode(self, mess, args):
        alarmPath = os.path.abspath(os.path.join(os.path.dirname(dataQuery.__file__), '../..', 'alarm'))
        all_modes = [f[:-4] for f in next(os.walk(alarmPath))[-1] if '.cfg' in f]

        modes = readMode()
        if len(args.split(' ')) == 1:
            actors = ['xcu_%s' % self.cam,
                      'ccd_%s' % self.cam]

            mode = args.split(' ')[0].strip().lower()

        elif len(args.split(' ')) == 2:
            actors = [args.split(' ')[0].strip().lower()]
            mode = args.split(' ')[1].strip().lower()
        else:
            return 'not enough argument'

        if mode not in all_modes:
            return 'unknown mode : %s \n modes availables :%s' % (mode, ','.join(all_modes))

        for actor in actors:
            modes[actor] = mode

        writeMode(modes)
        self.sendAlarmMsg(mess=mess, alarmMsg="%s in mode %s" % (','.join(actors), mode))

        return ''

    @botcmd(hidden=True)
    def kill(self, mess, args):
        self.shutdown()

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.get_ping() > self.PING_FREQUENCY:
            self._idle_ping()

        if self.PING_FREQUENCY and time.time() - self.get_alert() > self.ALERT_FREQ:
            self.ontimeout = self.timeoutHandler.ping()
            self.alarmHandler.checkValues()

            self._set_alert()

        if self.PING_FREQUENCY and time.time() - self.get_awake() > self.PING_FREQUENCY / 2:
            self._send_status()

    def thread_proc(self):
        pass

    def sendAlarmMsg(self, mess=False, alarmMsg=''):
        userAlarm = self.unPickle("userAlarm")

        for m in alarmMsg.split('\r\n'):
            self.log.debug(m)

        alarmMsg += ("  by %s  on %s" % (str(mess.getFrom().getNode()), dt.now().isoformat()[:19]) if mess else '')

        for jid in userAlarm.values():
            self.send(jid, alarmMsg)

    def updateJID(self, jid):
        userAlarm = self.unPickle("userAlarm")
        user = jid.getNode()
        self.log.info('updating jid : %s for user %s' % (jid, user))
        if user in userAlarm.iterkeys() and userAlarm[user] != jid:
            userAlarm[user] = jid
            self.doPickle('userAlarm', userAlarm)

    def loadConfig(self):
        devConf = loadConf()
        return [device for device in devConf if self.isRelevant(device.tablename)]

    def loadAlarm(self):
        alarmConf = loadAlarm()
        return [device for device in alarmConf if self.isRelevant(device.tablename)]

    def bindFunction(self, device):
        @botcmd
        def func1(self, mess=None, args=None):
            try:
                dataFrame = self.db.last(table=device.tablename,
                                         cols="%s" % ",".join([key for key in device.keys]))

                msg = dataFrame.strdate + "\n -= %s =- \n " % device.deviceLabel

                for label, unit, col in zip(device.labels, device.units, device.keys):
                    valStr = "{:g}".format(dataFrame[col])

                    msg += "%s (%s) = %s \n" % (label, unit, valStr)

                return msg

            except Exception as e:
                return str(e)

        funcName = str(device.botcmd)

        func1.__name__ = funcName
        setattr(func1, '__doc__', "Get %s current values" % device.deviceLabel)
        setattr(func1, '_jabberbot_command_name', funcName)
        setattr(self, funcName, types.MethodType(func1, self))

    def loadFunctions(self):
        for device in self.functionList:
            self.bindFunction(device)

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

    def isRelevant(self, tableName):
        actor = tableName.split('__')[0]
        return actor in self.actorList

    def constructPlot(self, mess, args, tdelta):
        user = mess.getFrom()
        rep = Report(self, tdelta, user)
        rep.start()

    @botcmd
    def plot(self, mess, args):
        """send a pdf report to your email address
           argument : duration in j,h or m
           ex : plot 1j
                plot 6h
                """
        knownUsers = self.unPickle("knownUsers")

        tdelta = None
        user = mess.getFrom().getNode()
        if user in knownUsers:

            ok = False
            fmt = [('j', 'days'), ('h', 'hours'), ('m', 'minutes'), ('d', 'days')]
            for f, kwarg in fmt:
                try:
                    val = int(args.split(f)[0])
                    d = {kwarg: val}
                    tdelta = timedelta(**d)
                    break
                except ValueError:
                    pass
            if tdelta is not None:
                self.constructPlot(mess, args, tdelta)
                return "Generating the report ..."
            else:
                return "unknown argument"

        else:
            return "Do I know you ? Send me your email address by using the command record "

    @botcmd
    def dataset(self, mess, args):
        """send a csv dataset to your email address
           argument : date1(Y-m-d) date2(Y-m-d) sampling period (seconds)
           ex : dataset 2017-09-01 2017-09-02 600
                """
        knownUsers = self.unPickle("knownUsers")

        if len(args.split(' ')) == 3:
            dstart = args.split(' ')[0].strip().lower()
            dend = args.split(' ')[1].strip().lower()
            step = float(args.split(' ')[2].strip().lower())
        else:
            return 'not enough arguments'

        user = mess.getFrom().getNode()
        if user in knownUsers:
            try:
                dstart = dt.strptime(dstart, "%Y-%m-%d")
            except ValueError:
                return "ValueError : time data '%s'" % dstart + " does not match format '%Y-%m-%d'"

            try:
                dend = dt.strptime(dend, "%Y-%m-%d")
            except ValueError:
                return "ValueError : time data '%s'" % dend + " does not match format '%Y-%m-%d'"

            dataset = Dataset(self, mess.getFrom(), dstart.isoformat(), dend.isoformat(), step)
            dataset.start()
            return "Generating the dataset ..."

        else:
            return "Do I know you ? Send me your email address by using the command record "
