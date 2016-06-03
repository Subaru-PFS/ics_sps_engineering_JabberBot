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

#
# This is an example JabberBot that serves as broadcasting server.
# Users can subscribe/unsubscribe to messages and send messages 
# by using "broadcast". It also shows how to send message from 
# outside the main loop, so you can inject messages into the bot 
# from other threads or processes, too.
#

import datetime as dt
import logging
import pickle
import threading
import time
import types
import os
import ConfigParser

from ics_sps_engineering_Lib_dataQuery import databaseManager
from myjabberbot import JabberBot, botcmd
from mythread import StoppableThread


class BroadcastingJabberBot(JabberBot):
    """This is a simple broadcasting client. Use "subscribe" to subscribe to broadcasts, "unsubscribe" to unsubscribe and "broadcast" + message to send out a broadcast message. Automatic messages will be sent out all 60 seconds."""

    def __init__(self, jid, password, parent, ip, port, path, users_alarm, users_subscribe, list_alarm, message_alarm,
                 kill_bot):
        self.list_function = []
        self.config_path = path.split('ics_sps_engineering_JabberBot')[0] + 'ics_sps_engineering_Lib_dataQuery/config/'
        self.loadCfg(self.config_path)
        for f, tableName, key, label, unit in self.list_function:
            self.bindFunction(f, tableName, key, label, unit)

        self.last_ping = time.time()
        self.servingForever = False
        self.database = databaseManager(ip, port)
        if self.database.initDatabase() == 1:
            self.databaseInitialized = True
        else:
            print ("Could not initiate database, check your network")
            self.databaseInitialized = False

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
        self.users_subscribe = users_subscribe
        self.list_alarm = list_alarm
        self.message_alarm = message_alarm
        self.message_queue = []
        self.actor = "xcu_r1__"
        self.getCommand()
        self.t0 = dt.datetime.now()

    def loadCfg(self, path):
        res = []
        config = ConfigParser.ConfigParser()
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
    def subscribe(self, mess, args):
        """Subscribe to the broadcast list"""
        user = mess.getFrom()
        if user in self.users_subscribe:
            return 'You are already subscribed.'
        else:
            self.users_subscribe.append(user)
            with open(self.path + 'user_subscribe', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.users_subscribe)
            self.log.info('%s subscribed to the broadcast.' % user)
            return 'You are now subscribed.'

    @botcmd
    def unsubscribe(self, mess, args):
        """Unsubscribe from the broadcast list"""
        user = mess.getFrom()
        if not user in self.users_subscribe:
            return 'You are not subscribed!'
        else:
            self.users_subscribe.remove(user)
            with open(self.path + 'user_subscribe', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.users_subscribe)
            self.log.info('%s unsubscribed from the broadcast.' % user)
            return 'You are now unsubscribed.'

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
    @botcmd(hidden=True)
    def broadcast(self, mess, args):
        """Sends out a broadcast, supply message as arguments (e.g. broadcast hello)"""
        self.message_queue.append('broadcast: %s (from %s)' % (args, str(mess.getFrom()),))
        self.log.info('%s sent out a message to %d users.' % (str(mess.getFrom()), len(self.users_subscribe),))

    @botcmd
    def alarm_msg(self, mess, args):
        """Sends out a broadcast to users on ALARM, supply message as arguments (e.g. broadcast hello)"""
        for user in self.users_alarm:
            self.send(user, 'broadcast: %s (from %s)' % (args, str(mess.getFrom())))

    @botcmd
    def alarm(self, mess, args):
        """Alarm acknowledgement, arguments : pressure|turbo|gatevalve|cooler """
        args = str(args)
        device = args.split(' ')[0].strip()
        command = args.split(' ')[1].strip()
        update_alarm = False
        if device in ["turbo", "cooler", "pressure", "gatevalve"]:
            if command == 'on':
                self.list_alarm[device] = True
                with open(self.path + 'list_alarm', 'w') as fichier:
                    mon_pickler = pickle.Pickler(fichier)
                    mon_pickler.dump(self.list_alarm)
                    for user in self.users_alarm:
                        self.send(user, "Alarm %s activated by %s  on %s" % (
                            device, str(mess.getFrom().getNode()),
                            dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
            elif command == 'off':
                self.list_alarm[device] = False
                with open(self.path + 'list_alarm', 'w') as fichier:
                    mon_pickler = pickle.Pickler(fichier)
                    mon_pickler.dump(self.list_alarm)
                    for user in self.users_alarm:
                        self.send(user, "Alarm %s desactivated by %s  on %s" % (
                            device, str(mess.getFrom().getNode()),
                            dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
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

    @botcmd
    def all(self, mess, args):
        """Get all parameters """
        user = mess.getFrom()
        res = ""
        res += "%s\n" % self.pressure(mess, args)
        res += "\n%s\n" % self.cooler(mess, args)
        res += "\n%s\n" % self.temperature(mess, args)
        res += "\n%s\n" % self.lam_temps1(mess, args)
        res += "\n%s" % self.lam_temps2(mess, args)
        self.send(user, res)

    @botcmd(hidden=True)
    def reboot_bot(self, mess, args):
        """reboot bot """
        self.parent.rebootBot()

    @botcmd(hidden=True)
    def curious_guy(self, mess, args):
        """WHO Suscribe to the alarm"""
        txt = "%s\n %s\n %s\n" % (','.join([str(user.getNode()) for user in self.users_alarm]),
                                  ','.join([str(user.getNode()) for user in self.users_subscribe]),
                                  str(self.list_alarm))

        return txt

    def bindFunction(self, funcName, tableName, key, label, unit):
        @botcmd
        def func1(self, mess=None, args=None):
            if self.ping_database():
                date, vals = self.database.getLastData(tableName, key)
                formats = ["{:.3e}" if uni.strip() in ['Torr', 'mBar', 'Bar']  else '{:.2f}' for uni in unit.split(',')]
                return date + "".join(
                    ["\n %s (%s) = %s" % (lab.strip(), uni.strip(), fmt.format(val)) for fmt, lab, uni, val in
                     zip(formats, label.split(','), unit.split(','), vals)])
            else:
                return "I could not reach your database, Let's try again"

        func1.__name__ = funcName
        setattr(func1, '_jabberbot_command_name', funcName)
        setattr(self, funcName, types.MethodType(func1, self))

    def checkCriticalValue(self):
        if self.ping_database():
            pressure_date, [pressure_val] = self.database.getLastData("vistherm__gauge", "pressure")
            turbospeed_date, [turbospeed_val] = self.database.getLastData(self.actor.lower() + "turbospeed", "val1")
            gatevalve_date, [gatevalve_val] = self.database.getLastData(self.actor.lower() + "gatevalve", "position")
            coolerPower_date, [coolerPower_val] = self.database.getLastData(self.actor.lower() + "coolertemps", "power")

            if float(pressure_val) > 1e-4:
                message = " WARNING    Pressure :  %s  (Torr)   on    %s" % (
                    '{:.3e}'.format(pressure_val), pressure_date)
                self.message_alarm["pressure"] = [message]

            if turbospeed_val < 90000:
                message = "WARNING    Turbo Speed : %s  (RPM) on   %s" % (str(turbospeed_val), turbospeed_date)
                self.message_alarm["turbo"] = [message]

            if gatevalve_val != 0:
                message = "WARNING    GateValve not OPENED anymore !  on    %s" % (gatevalve_date)
                self.message_alarm["gatevalve"] = [message]

            if not 70 < coolerPower_val < 265:
                message = "WARNING    Cooler Power : %s  (W)  on    %s" % (str(coolerPower_val), coolerPower_date)
                self.message_alarm["cooler"] = [message]

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

    def idle_proc(self):

        if self.PING_FREQUENCY \
                and time.time() - self.last_ping > self.PING_FREQUENCY:
            self.ping_database()
            self.last_ping = time.time()
        self._idle_ping()
        if not len(self.message_queue):
            return

        # copy the message queue, then empty it
        messages = self.message_queue
        self.message_queue = []
        for message in messages:
            if len(self.users_subscribe):
                self.log.info('sending "%s" to %d user(s).' % (message, len(self.users_subscribe),))
            for user in self.users_subscribe:
                self.send(user, message)

    def thread_proc(self):
        self.checkCriticalValue()
        if (dt.datetime.now() - self.t0).total_seconds() > 3600:
            turbo_text = self.turbo_speed()
            self.message_queue.append(turbo_text)
            pressure_text = self.pressure()
            self.message_queue.append(pressure_text)
            cooler_text = self.cooler()
            self.message_queue.append(cooler_text)
            temps_text = self.temperature()
            self.message_queue.append(temps_text)
            self.t0 = dt.datetime.now()

    def ping_database(self):
        if self.databaseInitialized:
            date, ping = self.database.getLastData("vistherm__gauge", "pressure")
            if type(ping) != int:
                return True
            else:
                self.log.info("Could not reach database, check your network")
                return False
        else:
            return False


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
                                  self.getUserAlarm(), self.getuserSubscribe(), self.getlistAlarm(),
                                  self.getMessageAlarm(), kill_old))
        self.nb_th.append(StoppableThread(self.nb_bot[-1]))
        self.nb_bot[-1].serve_forever(connect_callback=lambda: self.nb_th[-1].start(),
                                      disconnect_callback=lambda: self.rebootBot())

    def deleteBot(self):
        self.nb_bot[-1].log.info("%s   Deleting bot" % dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        self.nb_bot[-1].database.closeDatabase()
        self.nb_bot[-1].quit()
        if self.nb_bot[-1].servingForever:
            self.nb_th[-1].join()
        del (self.nb_bot[-1])
        del (self.nb_th[-1])

    def rebootBot(self):
        self.initialize_new_bot(kill_old=True)

    def getUserAlarm(self):
        with open(self.path + 'user_alarm', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()

    def getuserSubscribe(self):
        with open(self.path + 'user_subscribe', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()

    def getlistAlarm(self):
        with open(self.path + 'list_alarm', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()

    def getMessageAlarm(self):
        with open(self.path + 'message_alarm', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()
