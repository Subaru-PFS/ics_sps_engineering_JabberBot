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
import datetime as dt
import logging
import os
import pickle
import threading
import time
import types
from datetime import timedelta
from ics_sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager

from myjabberbot import JabberBot, botcmd
from mythread import StoppableThread
from report import Report


class BroadcastingJabberBot(JabberBot):
    """This is a simple broadcasting client """

    def __init__(self, jid, password, parent, ip, port, path, users_alarm, list_alarm, message_alarm, timeout_ack,
                 known_users,
                 kill_bot):
        self.list_function = []
        self.startingTime = dt.datetime.now()
        self.config_path = path.split('ics_sps_engineering_JabberBot')[0] + 'ics_sps_engineering_Lib_dataQuery/config/'
        self.loadCfg(self.config_path)
        for f, tableName, key, label, unit in self.list_function:
            self.bindFunction(f, tableName, key, label, unit)
        self.getTimeout()
        self.last_ping = time.time()
        self.servingForever = False
        self.db = DatabaseManager(ip, port)
        if self.db.initDatabase():
            print ("Initialization database OK")
            self.dbInitialized = True
        else:
            print ("Could not initiate database, check your network")
            self.dbInitialized = False

        super(BroadcastingJabberBot, self).__init__(jid, password)
        # create console handler
        if not kill_bot:
            chandler = logging.StreamHandler()
            # create formatter
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            # add formatter to handler
            chandler.setFormatter(formatter)
            # add handler to loggerZ
            self.log.addHandler(chandler)
            # set level to INFO
            self.log.setLevel(logging.DEBUG)
            logging.basicConfig(
                filename='%s/log/%s.log' % (path, dt.datetime.now().strftime("%Y-%m-%d_%H-%M")),
                level=logging.DEBUG)

        self.parent = parent
        self.path = path
        self.users_alarm = users_alarm
        self.list_alarm = list_alarm
        self.message_alarm = message_alarm
        self.known_users = known_users
        self.message_queue = []
        self.timeout_ack = timeout_ack
        self.actor = "xcu_r1__"
        self.getCommand()

    def loadCfg(self, path):
        res = []
        all_file = next(os.walk(path))[-1]
        for f in all_file:
            config = ConfigParser.ConfigParser()
            config.readfp(open(path + f))
            try:
                date = config.get('config_date', 'date')
                res.append((f, dt.datetime.strptime(date, "%d/%m/%Y")))
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

    @botcmd
    def alarm_mode(self, mess, args):
        """Be noticed by the alarms args : on/off"""
        args = str(args)
        if args in ['on', 'off']:
            user = mess.getFrom()
            if args.strip() == 'on':
                if user not in self.users_alarm:
                    self.users_alarm.append(user)
                    msg = "You are on Alarm MODE !"
                else:
                    msg = "Stop harassing me please !"
            else:
                if user in self.users_alarm:
                    self.users_alarm.remove(user)
                    msg = "You aren't on alarm MODE anymore !"
                else:
                    msg = "Are you kidding me !?"
            with open(self.path + 'user_alarm', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.users_alarm)
            return msg
        else:
            return 'unknown args'

    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list

    @botcmd
    def alarm_msg(self, mess, args):
        """Sends out a broadcast to users on ALARM, supply message as arguments (e.g. broadcast hello)"""
        for user in self.users_alarm:
            self.send(user, 'broadcast: %s (from %s)' % (args, str(mess.getFrom())))

    @botcmd
    def alarm(self, mess, args):
        """Alarm acknowledgement, arguments : pressure|turbo|gatevalve|cooler """
        args = str(args)
        if len(args.split(' ')) == 2:
            device = args.split(' ')[0].strip().lower()
            command = args.split(' ')[1].strip().lower()
            update_alarm = False
            if device in ["turbo", "cooler", "pressure", "gatevalve"]:
                if command == 'on':
                    if not self.list_alarm[device]:
                        self.list_alarm[device] = True
                        self.message_alarm[device] = []
                        with open(self.path + 'list_alarm', 'w') as fichier:
                            mon_pickler = pickle.Pickler(fichier)
                            mon_pickler.dump(self.list_alarm)
                            for user in self.users_alarm:
                                self.send(user, "Alarm %s activated by %s  on %s" % (
                                    device, str(mess.getFrom().getNode()),
                                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
                    else:
                        return "Alarm %s was already activated " % device
                elif command == 'off':
                    if self.list_alarm[device]:
                        self.list_alarm[device] = False
                        with open(self.path + 'list_alarm', 'w') as fichier:
                            mon_pickler = pickle.Pickler(fichier)
                            mon_pickler.dump(self.list_alarm)
                            for user in self.users_alarm:
                                self.send(user, "Alarm %s desactivated by %s  on %s" % (
                                    device, str(mess.getFrom().getNode()),
                                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
                    else:
                        return "Alarm %s was already desactivated " % device

                elif command == 'ack':
                    self.message_alarm[device] = []
                    for user in self.users_alarm:
                        self.send(user, "Alarm %s acknowledge by %s  on %s" % (
                            device, str(mess.getFrom().getNode()),
                            dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

                else:
                    return "unknown argument"
            else:
                return "no such device"
        else:
            return "not enough arguments"

    @botcmd
    def timeout(self, mess, args):
        """timout acknowledgement, arguments :  """
        args = str(args)
        if len(args.split(' ')) == 2:

            device = args.split(' ')[0].strip().lower()
            command = args.split(' ')[1].strip().lower()

            if device in self.list_timeout:
                if device in self.timeout_ack:
                    if command == 'rearm':
                        self.timeout_ack.remove(device)
                        with open(self.path + 'timeout_ack', 'w') as fichier:
                            mon_pickler = pickle.Pickler(fichier)
                            mon_pickler.dump(self.timeout_ack)
                            for user in self.users_alarm:
                                self.send(user, "Timeout rearm on  %s   by %s  on %s" % (
                                    device, str(mess.getFrom().getNode()),
                                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

                    elif command == 'ack':
                        return "Timeout %s was already acknowledge" % device
                    else:
                        return "unknown argument"

                else:
                    if command == 'ack':
                        self.timeout_ack.append(device)
                        with open(self.path + 'timeout_ack', 'w') as fichier:
                            mon_pickler = pickle.Pickler(fichier)
                            mon_pickler.dump(self.timeout_ack)
                            for user in self.users_alarm:
                                self.send(user, "Timeout ack on  %s   by %s  on %s" % (
                                    device, str(mess.getFrom().getNode()),
                                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
                    elif command == 'rearm':
                        return "Timeout %s was not acknowledge" % device
                    else:
                        return "unknown argument"
            else:
                return "no such device"
        else:
            return "not enough arguments"

    @botcmd
    def all(self, mess, args):
        """Get all parameters """
        user = mess.getFrom()
        res = ""
        res += "%s\n" % self.pressure(mess, args)
        res += "\n%s\n" % self.lam_pressure(mess, args)
        res += "\n%s\n" % self.cooler(mess, args)
        res += "\n%s\n" % self.temperature(mess, args)
        res += "\n%s\n" % self.lam_temps1(mess, args)
        res += "\n%s" % self.lam_temps2(mess, args)

        return res

    @botcmd
    def plot(self, mess, args):
        """send a pdf report to your email address
           argument : duration in j,h or m
           ex : plot 1j
                plot 6h
                """
        user = mess.getFrom()
        if user in self.known_users:
            ok = False
            fmt = [('j', 'days'), ('h', 'hours'), ('m', 'minutes')]
            for f, kwarg in fmt:
                try:
                    val = int(args.split(f)[0])
                    d = {kwarg: val}
                    tdelta = timedelta(**d)
                    ok = True
                    break
                except ValueError:
                    pass
            if ok:
                rep = Report(self.db, tdelta, self.known_users[user])
                if rep.reportSent:
                    return "I've just sent the report to %s" % self.known_users[user]
                else:
                    return "an error has occured"
            else:
                return "unknown argument"

        else:
            return "Do I know you ? Send me your email address by using the command record "

    @botcmd
    def record(self, mess, args):
        user = mess.getFrom()
        self.known_users[user] = args.strip()
        with open(self.path + 'known_users', 'w') as fichier:
            mon_pickler = pickle.Pickler(fichier)
            mon_pickler.dump(self.known_users)
            return "Thanks ! "

    @botcmd(hidden=True)
    def reboot_bot(self, mess, args):
        """reboot bot """
        self.parent.rebootBot()

    @botcmd(hidden=True)
    def curious_guy(self, mess, args):
        """WHO Suscribe to the alarm"""
        return "%s\n %s\n %s\n" % (
            ','.join([str(user.getNode()) for user in self.users_alarm]), str(self.list_alarm), str(self.list_timeout))

    def bindFunction(self, funcName, tableName, key, label, unit):
        @botcmd
        def func1(self, mess=None, args=None):
            if self.ping_database():

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
            else:
                return "I could not reach your database, Let's try again"

        func1.__name__ = funcName
        setattr(func1, '_jabberbot_command_name', funcName)
        setattr(self, funcName, types.MethodType(func1, self))

    def checkCriticalValue(self):
        if self.ping_database():
            self.checkPressure()
            self.checkTurbo()
            self.checkGatevalve()
            self.checkCooler()

            if self.list_alarm["pressure"]:
                if self.message_alarm["pressure"]:
                    for user in self.users_alarm:
                        self.send(user, self.message_alarm["pressure"][0])

            if self.list_alarm["turbo"]:
                if self.message_alarm["turbo"]:
                    for user in self.users_alarm:
                        self.send(user, self.message_alarm["turbo"][0])

            if self.list_alarm["gatevalve"]:
                if self.message_alarm["gatevalve"]:
                    for user in self.users_alarm:
                        self.send(user, self.message_alarm["gatevalve"][0])

            if self.list_alarm["cooler"]:
                if self.message_alarm["cooler"]:
                    for user in self.users_alarm:
                        self.send(user, self.message_alarm["cooler"][0])

            with open(self.path + 'message_alarm', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.message_alarm)

    def checkPressure(self):
        thresh = 1e-8, 1e-4
        return_values = self.db.getLastData("vistherm__gauge", "pressure")
        if type(return_values) is int:
            self.log.error("Error while checking pressure")
        else:
            date, [pressure_val] = return_values
            if not thresh[0] < pressure_val < thresh[1]:
                message = "%s\n" \
                          "        WARNING !        \n" \
                          "Pressure (Torr) :  %.3e\n" \
                          "    OUT OF RANGE !    \n(%.1e < Pressure < %.1e)" % (
                              date, pressure_val, thresh[0], thresh[1])
                self.message_alarm["pressure"] = [message]

    def checkTurbo(self):
        thresh = 89900, 90100
        return_values = self.db.getLastData(self.actor.lower() + "turbospeed", "val1")
        if type(return_values) is int:
            self.log.error("Error while checking turbo")
        else:
            date, [turbospeed_val] = return_values
            if not thresh[0] < turbospeed_val < thresh[1]:
                message = "%s\n" \
                          "        WARNING !        \n" \
                          "Turbo Speed (RPM) :  %i\n" \
                          "    OUT OF RANGE !    \n(%i < Speed < %i)" % (date, turbospeed_val, thresh[0], thresh[1])
                self.message_alarm["turbo"] = [message]

    def checkGatevalve(self):
        return_values = self.db.getLastData(self.actor.lower() + "gatevalve", "position")
        if type(return_values) is int:
            self.log.error("Error while checking gatevalve")
        else:
            date, [gatevalve_val] = return_values
            if gatevalve_val != 0:
                message = "%s\n" \
                          "        WARNING !        \n" \
                          "Gatevalve not OPENED anymore !" % date
                self.message_alarm["gatevalve"] = [message]

    def checkCooler(self):
        thresh = 70, 250
        return_values = self.db.getLastData(self.actor.lower() + "coolertemps", "power")
        if type(return_values) is int:
            self.log.error("Error while checking cooler")
        else:
            date, [coolerPower_val] = return_values
            if not thresh[0] < coolerPower_val < thresh[1]:
                message = "%s\n" \
                          "        WARNING !        \n" \
                          "Cooler Power (W) :  %i\n" \
                          "    OUT OF RANGE !    \n(%i < Power < %i)" % (date, coolerPower_val, thresh[0], thresh[1])
                self.message_alarm["cooler"] = [message]

    def idle_proc(self):
        if self.PING_FREQUENCY and time.time() - self.last_ping > self.PING_FREQUENCY:
            self.ping_database()
            self.checkTimeout()
            self.last_ping = time.time()
        self._idle_ping()

    def thread_proc(self):
        self.checkCriticalValue()
        self.sendTimeout()

    def ping_database(self):
        if self.dbInitialized:
            return_values = self.db.getLastData("vistherm__gauge", "pressure")
            if type(return_values) is not int:
                return True
            else:
                self.log.error("Could not reach database, check your network")
                return False
        else:
            return False

    def getTimeout(self):

        self.timeout_limit = 90
        self.list_timeout = [tableName for f, tableName, key, label, unit in self.list_function]
        self.last_date = {}
        self.last_time = {}
        for f, tableName, key, label, unit in self.list_function:
            self.last_date[tableName] = 0
            self.last_time[tableName] = dt.datetime.now()

    def checkTimeout(self):
        if self.dbInitialized:
            for f, tableName, key, label, unit in self.list_function:
                return_values = self.db.getLastData(tableName, "id")
                if return_values == -5:
                    self.log.error("Could not reach database, check your network")
                elif type(return_values) is int:
                    self.log.error("Error keyword : %s" % tableName)
                else:
                    date, id = return_values

                    if date != self.last_date[tableName]:
                        if self.last_date[tableName] != 0:
                            if tableName in self.list_timeout:
                                self.list_timeout.remove(tableName)
                        self.last_time[tableName] = dt.datetime.now()
                        self.last_date[tableName] = date
                    else:
                        if (dt.datetime.now() - self.last_time[tableName]).total_seconds() > self.timeout_limit:
                            if tableName not in self.list_timeout:
                                self.list_timeout.append(tableName)

    def sendTimeout(self):
        if (dt.datetime.now() - self.startingTime).total_seconds() > self.timeout_limit:
            for device in self.list_timeout:
                if device not in self.timeout_ack:
                    for user in self.users_alarm:
                        self.send(user, "TIME OUT ON %s ! ! ! \r" % device)

    def tellAwake(self):
        for user in self.users_alarm:
            self.send(user,
                      "It's %s UTC and I just woke up. \r  Have a nice day or night whatever ..." % dt.datetime.now().strftime(
                          "%H:%M"))


class JabberBotManager(threading.Thread):
    """This prevent the JabberBot to be disconnected from server"""

    def __init__(self, path, ip, port, jid, password):
        super(JabberBotManager, self).__init__()
        self.path = path
        self.ip = ip
        self.port = port
        self.jid = jid
        self.password = password
        self.nb_bot = []
        self.nb_th = []
        self.start()

        self.initialize_new_bot()

    def initialize_new_bot(self, kill_old=False):
        if kill_old:
            self.deleteBot()
            time.sleep(150)
        self.nb_bot.append(
            BroadcastingJabberBot(self.jid, self.password, self, self.ip, self.port, self.path,
                                  self.getUserAlarm(), self.getListAlarm(), self.getMessageAlarm(), self.getTimeout(),
                                  self.getKnownUsers(),
                                  kill_old))
        self.nb_th.append(StoppableThread(self.nb_bot[-1]))
        self.nb_bot[-1].serve_forever(connect_callback=lambda: self.nb_th[-1].start(),
                                      disconnect_callback=lambda: self.rebootBot())

    def deleteBot(self):
        self.nb_bot[-1].log.info("%s   Deleting bot" % dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        self.nb_bot[-1].db.closeDatabase()
        self.nb_bot[-1].quit()
        if self.nb_bot[-1].servingForever:
            self.nb_th[-1].join()
        del (self.nb_bot[-1])
        del (self.nb_th[-1])

    def rebootBot(self):
        self.initialize_new_bot(kill_old=True)

    def getUserAlarm(self):
        try:
            with open(self.path + 'user_alarm', 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating empty user alarm file"
            return []

    def getListAlarm(self):
        try:
            with open(self.path + 'list_alarm', 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating empty list alarm file"
            return {"pressure": False, "turbo": False, "gatevalve": False, "cooler": False}

    def getKnownUsers(self):
        try:
            with open(self.path + 'known_users', 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating empty known_users file"
            return {}

    def getMessageAlarm(self):
        try:
            with open(self.path + 'message_alarm', 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating empty message alarm file"
            return {"pressure": [], "turbo": [], "gatevalve": [], "cooler": []}

    def getTimeout(self):
        try:
            with open(self.path + 'timeout_ack', 'r') as fichier:
                mon_depickler = pickle.Unpickler(fichier)
                return mon_depickler.load()
        except IOError:
            print "creating timeout_ack file"
            return []
