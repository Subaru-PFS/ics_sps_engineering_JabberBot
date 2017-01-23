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


class PfsJabberBot(JabberBot):
    """This is a simple broadcasting client """
    TIMEOUT_LIM = 20

    def __init__(self, chandler, jid, password, absPath, addr, port):

        self.list_function = []
        self.thread_killed = False
        self.path = absPath
        self.last_ping = time.time()

        self.userAlarm = self.getList("userAlarm")
        self.listAlarm = self.getDict("listAlarm")
        self.timeoutAck = self.getList("timeoutAck")
        self.knownUsers = self.getDict("knownUsers")

        self.db = DatabaseManager(addr, port)
        self.db.initDatabase()

        config_path = absPath.split('ics_sps_engineering_JabberBot')[0] + 'ics_sps_engineering_Lib_dataQuery/config/'
        self.loadCfg(config_path)
        self.loadAlarm(config_path)
        self.loadFunctions()
        self.loadTimeout()

        JabberBot.__init__(self, jid, password)
        # add handler to logger
        self.log.addHandler(chandler)
        # set level to INFO
        self.log.setLevel(logging.DEBUG)

        self._getCommand()

    @botcmd
    def alarm_mode(self, mess, args):
        """Be noticed by the alarms args : on/off"""
        args = str(args)
        if args in ['on', 'off']:
            user = mess.getFrom()
            if args.strip() == 'on':
                if user not in self.userAlarm:
                    self.userAlarm.append(user)
                    msg = "You are on Alarm MODE !"
                else:
                    msg = "Stop harassing me please !"
            else:
                if user in self.userAlarm:
                    self.userAlarm.remove(user)
                    msg = "You aren't on alarm MODE anymore !"
                else:
                    msg = "Are you kidding me !?"
            with open(self.path + 'userAlarm', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.userAlarm)
            return msg
        else:
            return 'unknown args'

    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list

    @botcmd
    def alarm_msg(self, mess, args):
        """Sends out a broadcast to users on ALARM, supply message as arguments (e.g. broadcast hello)"""
        for user in self.userAlarm:
            self.send(user, 'broadcast: %s (from %s)' % (args, str(mess.getFrom())))

    @botcmd
    def alarm(self, mess, args):
        """alarm pressure|turbo|gatevalve|cooler  ack|off|on """
        args = str(args)
        kind = {'on': 'activated', 'off': 'desactivated', 'ack': 'acknowledge'}

        if len(args.split(' ')) == 2:
            device = args.split(' ')[0].strip().lower()
            command = args.split(' ')[1].strip().lower()

            if device in self.listAlarm.iterkeys():
                if command == 'on':
                    if not self.listAlarm[device]:
                        self.listAlarm[device] = True
                        self.messageAlarm[device] = []
                        with open(self.path + 'listAlarm', 'w') as fichier:
                            mon_pickler = pickle.Pickler(fichier)
                            mon_pickler.dump(self.listAlarm)

                    else:
                        return "Alarm %s was already activated " % device
                elif command == 'off':
                    if self.listAlarm[device]:
                        self.listAlarm[device] = False
                        with open(self.path + 'listAlarm', 'w') as fichier:
                            mon_pickler = pickle.Pickler(fichier)
                            mon_pickler.dump(self.listAlarm)

                    else:
                        return "Alarm %s was already desactivated " % device

                elif command == 'ack':
                    self.messageAlarm[device] = []

                else:
                    return "unknown argument"
            else:
                return "no such device"
        else:
            return "not enough arguments"

        for user in self.userAlarm:
            self.send(user, "Alarm %s %s by %s  on %s" % (device,
                                                          kind[command],
                                                          str(mess.getFrom().getNode()),
                                                          dt.now().strftime("%d/%m/%Y %H:%M:%S")))

    @botcmd
    def timeout(self, mess, args):
        """timeout tableName ack|rearm """

        args = str(args)
        if len(args.split(' ')) == 2:

            device = args.split(' ')[0].strip().lower()
            command = args.split(' ')[1].strip().lower()

            tableNames = [tableName for f, tableName, key, label, unit in self.list_function]
            if device not in tableNames:
                return "no such device"

            if command == 'rearm':
                if device in self.timeoutAck:
                    self.timeoutAck.remove(device)
                    with open(self.path + 'timeoutAck', 'w') as fichier:
                        mon_pickler = pickle.Pickler(fichier)
                        mon_pickler.dump(self.timeoutAck)

                else:
                    return "Timeout %s was not acknowledge" % device

            elif command == 'ack':
                if device not in self.timeoutAck:
                    self.timeoutAck.append(device)
                    with open(self.path + 'timeoutAck', 'w') as fichier:
                        mon_pickler = pickle.Pickler(fichier)
                        mon_pickler.dump(self.timeoutAck)

                else:
                    return "Timeout %s was already acknowledge" % device
            else:
                return "unknown argument"

        else:
            return "not enough arguments"

        for user in self.userAlarm:
            self.send(user, "Timeout %s  on  %s   by %s  on %s" % (device,
                                                                   command,
                                                                   str(mess.getFrom().getNode()),
                                                                   dt.now().strftime("%d/%m/%Y %H:%M:%S")))

    @botcmd
    def all(self, mess, args):
        """Get all parameters """
        user = mess.getFrom()
        res = ""
        for attr in ['pressure', 'frontpressure', 'lam_pressure',
                     'cooler', 'temperature', 'ccd_temps', 'lam_temps1', 'lam_temps2']:

            try:
                func = getattr(self, attr)
                res += "\n%s\n" % func(mess, args)
            except:
                pass

        return res

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
                rep = Report(self.db, tdelta, self.knownUsers[user])
                if rep.reportSent:
                    return "I've just sent the report to %s" % self.knownUsers[user]
                else:
                    return "an error has occured"
            else:
                return "unknown argument"

        else:
            return "Do I know you ? Send me your email address by using the command record "

    @botcmd
    def record(self, mess, args):
        user = mess.getFrom().getNode()
        self.knownUsers[user] = args.strip()
        with open(self.path + 'knowUsers', 'w') as fichier:
            mon_pickler = pickle.Pickler(fichier)
            mon_pickler.dump(self.knownUsers)
            return "Thanks ! "

    @botcmd(hidden=True)
    def curious_guy(self, mess, args):
        """WHO Suscribe to the alarm"""
        return "%s\n %s\n %s\n" % (','.join([str(user.getNode()) for user in self.userAlarm]),
                                   str(self.listAlarm),
                                   str(self.timeoutAck))

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.last_ping > self.PING_FREQUENCY:
            self.checkTimeout()
            self.checkCriticalValue()
            self.last_ping = time.time()
        self._idle_ping()

    def thread_proc(self):
        t = 60
        for i in range(int(t // 0.1)):
            if self.thread_killed:
                return
            time.sleep(0.1)
        self._send_status()
        self.sendAlert()

    def sendAlert(self):

        for device in self.listTimeout:
            if device not in self.timeoutAck:
                for user in self.userAlarm:
                    self.send(user, "TIME OUT ON %s ! ! ! \r" % device)
        for device in self.criticalDevice:
            name = device["label"].lower()
            if self.listAlarm[name] and self.messageAlarm[name]:
                for user in self.userAlarm:
                    self.send(user, self.messageAlarm[name][0])

    def checkCriticalValue(self):

        for device in self.criticalDevice:
            name = device["label"].lower()
            return_values = self.db.getLastData(device["tablename"], device["key"])

            if type(return_values) is not int:
                date, [val] = return_values
                fmt = "{:.5e}" if len(str(val)) > 8 else "{:.2f}"
                if not float(device["lower_bound"]) <= val < float(device["higher_bound"]):
                    msg = "WARNING ! %s OUT OF RANGE \r %s <= %s < %s" % (device["label"],
                                                                          device["lower_bound"],
                                                                          fmt.format(val),
                                                                          device["higher_bound"])

                    self.messageAlarm[name] = [msg]

    def checkTimeout(self):

        for f, tableName, key, label, unit in self.list_function:
            return_values = self.db.getLastData(tableName, "id")
            if return_values == -5:
                self.log.error("Could not reach database, check your network")
            elif type(return_values) is int:
                self.log.error("Error keyword : %s" % tableName)
            else:

                date, id = return_values
                prev_date, prev_time = self.last_date[tableName]
                if prev_date != date:
                    self.last_date[tableName] = date, dt.now()
                    if tableName in self.listTimeout:
                        self.listTimeout.remove(tableName)
                else:
                    if (dt.now() - prev_time).total_seconds() > PfsJabberBot.TIMEOUT_LIM:
                        if tableName not in self.listTimeout:
                            self.listTimeout.append(tableName)


    def loadCfg(self, path):
        res = []
        all_file = next(os.walk(path))[-1]
        for f in all_file:
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
                self.list_function.append((fname, tableName, key, label, unit))

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

    def loadTimeout(self):
        self.listTimeout = []
        self.last_date = {}

        for f, tableName, key, label, unit in self.list_function:
            self.last_date[tableName] = 0, dt.now()

    def bindFunction(self, funcName, tableName, key, label, unit):
        @botcmd
        def func1(self, mess=None, args=None):
            return_values = self.db.getLastData(tableName, key)
            if type(return_values) is not int:
                date, vals = return_values
                formats = ["{:.3e}" if uni.strip() in ['Torr', 'mBar', 'Bar'] else '{:.2f}' for uni in
                           unit.split(',')]
                return date + "".join(
                    ["\n %s (%s) = %s" % (lab.strip(), uni.strip(), fmt.format(val)) for fmt, lab, uni, val in
                     zip(formats, label.split(','), unit.split(','), vals)])
            else:
                return "error code : %i" % return_values

        func1.__name__ = funcName
        setattr(func1, '_jabberbot_command_name', funcName)
        setattr(self, funcName, types.MethodType(func1, self))

    def loadFunctions(self):
        for f, tableName, key, label, unit in self.list_function:
            self.bindFunction(f, tableName, key, label, unit)

    def tellAwake(self):
        for user in self.userAlarm:
            self.send(user, "It's %s UTC and I just woke up. \r  Have a nice day or night whatever ..." %
                      dt.now().strftime("%H:%M"))

    def getList(self, filename):
        try:
            with open(self.path + filename, 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating empty %s file" % filename
            return []

    def getDict(self, filename):
        try:
            with open(self.path + filename, 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating empty %s file" % filename
            return {}
