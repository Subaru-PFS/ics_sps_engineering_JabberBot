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

import ConfigParser
import logging
import os
import pickle
import time
import types
from datetime import datetime as dt
from datetime import timedelta

from ics_sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager

from myjabberbot import JabberBot, botcmd
from report import Report
from dataset import Dataset


class PfsBot(JabberBot):
    """This is a simple broadcasting client """
    TIMEOUT_LIM = 90
    ALERT_FREQ = 60

    def __init__(self, jid, password, absPath, logFolder, addr, port, actorList):
        self.log = logging.getLogger('JabberBot.PfsBot')

        self.logFolder = logFolder
        self.db_addr = addr
        self.db_port = port
        self.actorList = actorList
        self.list_function = []
        self.curveDict = {}
        self.thread_killed = False
        self.path = absPath
        self.last_alert = time.time()
        self.last_awake = time.time()

        self.loadStatus()

        self.db = DatabaseManager(addr, port)
        self.db.initDatabase()

        config_path = absPath.split('ics_sps_engineering_JabberBot')[0] + 'ics_sps_engineering_Lib_dataQuery/config/'
        self.config_path = config_path
        self.loadCfg(config_path)
        self.loadAlarm(config_path)
        self.loadFunctions()
        self.loadTimeout()

        JabberBot.__init__(self, jid, password)

        self._getCommand()

    @property
    def cam(self):
        return self.actorList[-1].split('__')[-1].split('_')[-1]

    def loadStatus(self):
        self.userAlarm = self.unPickle("userAlarm")
        self.listAlarm = self.unPickle("listAlarm")
        self.timeoutAck = self.unPickle("timeoutAck", empty="list")
        self.knownUsers = self.unPickle("knownUsers")


    @botcmd
    def alarm_mode(self, mess, args):
        """Be noticed by the alarms args : on/off"""
        self.loadStatus()

        args = str(args)
        if args in ['on', 'off']:
            user = mess.getFrom().getNode()
            if args.strip() == 'on':
                if user not in self.userAlarm.iterkeys():
                    self.userAlarm[user] = mess.getFrom()
                    msg = "You are on Alarm MODE !"
                else:
                    msg = "Stop harassing me please !"
            else:
                if user in self.userAlarm.iterkeys():
                    self.userAlarm.pop(user, None)
                    msg = "You aren't on alarm MODE anymore !"
                else:
                    msg = "Are you kidding me !?"
            with open(self.path + 'userAlarm', 'w') as thisFile:
                pickler = pickle.Pickler(thisFile)
                pickler.dump(self.userAlarm)
            return msg
        else:
            return 'unknown args'

    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list


    @botcmd
    def alarm_msg(self, mess, args):
        """Sends out a broadcast to users on ALARM, supply message as arguments (e.g. broadcast hello)"""
        self.sendAlarmMsg('broadcast: %s (from %s)' % (args, str(mess.getFrom())))

    @botcmd
    def alarm(self, mess, args):
        """alarm pressure|turbo|gatevalve|cooler  ack|off|on """
        self.loadStatus()

        args = str(args)
        kind = {'on': 'activated', 'off': 'desactivated', 'ack': 'acknowledge'}

        if len(args.split(' ')) == 2:
            device = args.split(' ')[0].strip().lower()
            command = args.split(' ')[1].strip().lower()
            if device not in self.listAlarm.iterkeys():
                device = '%s-%s' % (device, self.cam)
            if device in self.listAlarm.iterkeys():
                if command == 'on':
                    if not self.listAlarm[device]:
                        self.listAlarm[device] = True
                        self.messageAlarm[device] = []
                        with open(self.path + 'listAlarm', 'w') as thisFile:
                            pickler = pickle.Pickler(thisFile)
                            pickler.dump(self.listAlarm)

                    else:
                        return "Alarm %s was already activated " % device
                elif command == 'off':
                    if self.listAlarm[device]:
                        self.listAlarm[device] = False
                        with open(self.path + 'listAlarm', 'w') as thisFile:
                            pickler = pickle.Pickler(thisFile)
                            pickler.dump(self.listAlarm)

                    else:
                        return "Alarm %s was already desactivated " % device

                elif command == 'ack':
                    self.messageAlarm[device] = []

                else:
                    return "unknown argument, I'm sure you meant on, off or ack"
            else:
                return "device does not exist ! devices available : \n" + '\n'.join(
                    [d for d in self.listAlarm.iterkeys()])
        else:
            return "not enough arguments, it's 'alarm device on|off|ack|rearm' FYI...  "
        self.sendAlarmMsg("Alarm %s %s by %s  on %s" % (device,
                                                        kind[command],
                                                        str(mess.getFrom().getNode()),
                                                        dt.now().strftime("%d/%m/%Y %H:%M:%S")))

    @botcmd
    def timeout(self, mess, args):
        """timeout device ack|rearm """
        self.loadStatus()

        args = str(args)
        if len(args.split(' ')) == 2:

            device = args.split(' ')[0].strip().lower()
            command = args.split(' ')[1].strip().lower()

            tableNames = [tableName for f, tableName, key, label, unit, labelDevice in self.list_function]

            if device not in tableNames:
                return "device does not exist ! devices available : \n" + '\n'.join(tableNames)

            if command == 'rearm':
                if device in self.timeoutAck:
                    self.timeoutAck.remove(device)
                    with open(self.path + 'timeoutAck', 'w') as thisFile:
                        pickler = pickle.Pickler(thisFile)
                        pickler.dump(self.timeoutAck)

                else:
                    return "Timeout %s was not acknowledge" % device

            elif command == 'ack':
                if device not in self.timeoutAck:
                    self.timeoutAck.append(device)
                    with open(self.path + 'timeoutAck', 'w') as thisFile:
                        pickler = pickle.Pickler(thisFile)
                        pickler.dump(self.timeoutAck)

                else:
                    return "Timeout %s was already acknowledge" % device
            else:
                return "unknown argument, I'm sure you meant ack or rearm"

        else:
            return "not enough arguments, it's 'timeout devices ack|rearm' FYI...  "

        self.sendAlarmMsg("Timeout %s  %s   by %s  on %s" % (device,
                                                             command,
                                                             str(mess.getFrom().getNode()),
                                                             dt.now().strftime("%d/%m/%Y %H:%M:%S")))

    @botcmd
    def all(self, mess, args):
        """Get all parameters """
        user = mess.getFrom()
        res = ""
        for attr in ['pressure', 'frontpressure', 'lam_pressure','ionpump1','ionpump2',
                     'cooler', 'temperature', 'ccd_temps', 'lam_temps1', 'lam_temps2']:

            try:
                func = getattr(self, attr)
                res += "\n%s\n" % func(mess, args)
            except:
                pass

        return res

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

        tdelta = None
        user = mess.getFrom().getNode()
        if user in self.knownUsers:
            ok = False
            fmt = [('j', 'days'), ('h', 'hours'), ('m', 'minutes')]
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
        if len(args.split(' ')) == 3:
            dstart = args.split(' ')[0].strip().lower()
            dend = args.split(' ')[1].strip().lower()
            step = float(args.split(' ')[2].strip().lower())
        else:
            return 'not enough arguments'

        user = mess.getFrom().getNode()
        if user in self.knownUsers:
            dstart = dt.strptime(dstart, "%Y-%m-%d")
            dend = dt.strptime(dend, "%Y-%m-%d")
            dataset = Dataset(self, mess.getFrom(), dstart, dend, step)
            dataset.start()
            return "Generating the dataset ..."

        else:
            return "Do I know you ? Send me your email address by using the command record "

    @botcmd
    def record(self, mess, args):
        self.loadStatus()
        user = mess.getFrom().getNode()
        self.knownUsers[user] = args.strip()
        with open(self.path + 'knowUsers', 'w') as thisFile:
            pickler = pickle.Pickler(thisFile)
            pickler.dump(self.knownUsers)
            return "Thanks ! "

    @botcmd(hidden=True)
    def curious_guy(self, mess, args):
        """WHO Suscribe to the alarm"""
        self.loadStatus()

        return "%s\n %s\n %s\n" % (str([jid for jid in self.userAlarm.iterkeys()]),
                                   str(self.listAlarm), str(self.timeoutAck))

    @botcmd(hidden=True)
    def kill(self, mess, args):
        self.shutdown()

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.get_ping() > self.PING_FREQUENCY:
            self._idle_ping()
            self.checkTimeout()
            self.checkCriticalValue()

        if self.PING_FREQUENCY and time.time() - self.last_alert > self.ALERT_FREQ:
            self.loadStatus()
            self.sendAlert()
            self.last_alert = time.time()

        if self.PING_FREQUENCY and time.time() - self.last_awake > 6:
            self._send_status()
            self.last_awake = time.time()

    def thread_proc(self):
        pass

    def sendAlert(self):

        for device in self.listTimeout:
            if device not in self.timeoutAck and self.isRelevant(device):
                self.sendAlarmMsg("TIME OUT ON %s ! ! !" % device)
        for device in self.criticalDevice:
            name = device["label"].lower()
            if self.listAlarm[name] and self.messageAlarm[name] and self.isRelevant(device["tablename"]):
                self.sendAlarmMsg(self.messageAlarm[name][0])

    def checkCriticalValue(self):

        for device in self.criticalDevice:
            name = device["label"].lower()
            return_values = self.db.getLastData(device["tablename"], device["key"])

            if type(return_values) is not int:
                date, [val] = return_values
                fmt = "{:.5e}" if len(str(val)) > 8 else "{:.2f}"
                if not float(device["lower_bound"]) <= val < float(device["higher_bound"]):
                    msg = "WARNING ! %s OUT OF RANGE \r\n %s <= %s < %s" % (device["label"],
                                                                            device["lower_bound"],
                                                                            fmt.format(val),
                                                                            device["higher_bound"])

                    self.messageAlarm[name] = [msg]

    def checkTimeout(self):

        for f, tableName, key, label, unit, labelDevice in self.list_function:
            return_values = self.db.getLastData(tableName, "id")
            if return_values == -5:
                self.log.debug("Could not reach database, check your network")
            elif type(return_values) is int:
                self.log.debug("Error keyword : %s" % tableName)
            else:

                date, id = return_values
                prev_date, prev_time = self.last_date[tableName]
                if prev_date != date:
                    self.last_date[tableName] = date, dt.now()
                    if tableName in self.listTimeout:
                        self.listTimeout.remove(tableName)
                else:
                    if (dt.now() - prev_time).total_seconds() > PfsBot.TIMEOUT_LIM:
                        if tableName not in self.listTimeout:
                            self.listTimeout.append(tableName)

    def sendAlarmMsg(self, mess):
        for m in mess.split('\r\n'):
            self.log.debug(m)
        for jid in self.userAlarm.values():
            self.send(jid, mess)

    def updateJID(self, jid):
        user = jid.getNode()
        if user in self.userAlarm.iterkeys() and self.userAlarm[user] != jid:
            self.userAlarm[user] = jid
            with open(self.path + 'userAlarm', 'w') as thisFile:
                pickler = pickle.Pickler(thisFile)
                pickler.dump(self.userAlarm)

    def loadCfg(self, path):
        res = []
        allFile = next(os.walk(path))[-1]
        for f in allFile:
            config = ConfigParser.ConfigParser()
            config.readfp(open(path + f))
            try:
                date = config.get('config_date', 'date')
                res.append((f, dt.strptime(date, "%d/%m/%Y")))
            except ConfigParser.NoSectionError:
                pass
        res.sort(key=lambda tup: tup[1])
        config = ConfigParser.ConfigParser()
        config.readfp(open(path + res[-1][0]))
        for a in config.sections():
            if a != 'config_date':
                tableName = a
                fname = config.get(a, "bot_cmd")
                key = config.get(a, 'key')
                label = config.get(a, 'label')
                unit = config.get(a, 'unit')
                labelDevice = config.get(a, 'label_device')
                if self.isRelevant(tableName):
                    self.list_function.append((fname, tableName.lower(), key, label, unit, labelDevice))
                    for k, l, t in zip([k.strip() for k in key.split(',')],
                                       [l.strip() for l in label.split(',')],
                                       [t.strip() for t in config.get(a, 'type').split(',')]):
                        self.curveDict["%s-%s" % (tableName, k)] = labelDevice, t, l

    def loadAlarm(self, path):

        self.criticalDevice = []
        self.messageAlarm = {}
        config = ConfigParser.ConfigParser()
        config.readfp(open(path + 'alarm.cfg'))
        for a in config.sections():
            dict = {"label": a}
            for b in config.options(a):
                dict[b] = config.get(a, b)
            self.criticalDevice.append(dict)
        for device in self.criticalDevice:
            try:
                name = device["label"].lower()
                a = self.listAlarm[name]
            except KeyError:
                self.listAlarm[name] = False

            self.messageAlarm[name] = []

        with open(self.path + 'listAlarm', 'w') as thisFile:
            pickler = pickle.Pickler(thisFile)
            pickler.dump(self.listAlarm)

    def loadTimeout(self):
        self.listTimeout = []
        self.last_date = {}

        for f, tableName, key, label, unit, labelDevice in self.list_function:
            self.last_date[tableName] = 0, dt.now()

    def bindFunction(self, funcName, tableName, key, label, unit, labelDevice):
        @botcmd
        def func1(self, mess=None, args=None):
            return_values = self.db.getLastData(tableName, key)
            if type(return_values) is not int:
                date, vals = return_values
                formats = ["{:.3e}" if uni.strip() in ['Torr', 'mBar', 'Bar'] else '{:.2f}' for uni in
                           unit.split(',')]
                return date + "\n -= %s =-" % labelDevice + "".join(
                    ["\n %s (%s) = %s" % (lab.strip(), uni.strip(), fmt.format(val)) for fmt, lab, uni, val in
                     zip(formats, label.split(','), unit.split(','), vals)])
            else:
                return "error code : %i" % return_values

        func1.__name__ = funcName
        setattr(func1, '__doc__', "Get %s current values" % labelDevice)
        setattr(func1, '_jabberbot_command_name', funcName)
        setattr(self, funcName, types.MethodType(func1, self))

    def loadFunctions(self):
        for f, tableName, key, label, unit, labelDevice in self.list_function:
            self.bindFunction(f, tableName, key, label, unit, labelDevice)

    def tellAwake(self):

        self.sendAlarmMsg("It's %s UTC and I just woke up. \r  Have a nice day or night whatever ..."
                          % dt.now().strftime("%H:%M"))

    def unPickle(self, filename, empty=None):
        try:
            with open(self.path + filename, 'r') as thisFile:
                unpickler = pickle.Unpickler(thisFile)
                return unpickler.load()
        except IOError:
            self.log.debug("creating empty %s file" % filename)
            return {} if empty is None else []

    def isRelevant(self, tableName):
        actor = tableName.split('__')[0]
        if actor in self.actorList:
            return True
        else:
            return False
