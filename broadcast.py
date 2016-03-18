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

from ics_sps_engineering_Lib_dataQuery import databaseManager

from myjabberbot import JabberBot, botcmd
from mythread import StoppableThread


class BroadcastingJabberBot(JabberBot):
    """This is a simple broadcasting client. Use "subscribe" to subscribe to broadcasts, "unsubscribe" to unsubscribe and "broadcast" + message to send out a broadcast message. Automatic messages will be sent out all 60 seconds."""

    def __init__(self, jid, password, parent, ip, port, path, users_alarm, users_subscribe, alarm_ack,
                 kill_bot):
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
        self.alarm_ack = alarm_ack
        self.message_queue = []
        self.actor = "xcu_r1__"
        self.database = databaseManager(ip, port)
        self.t0 = dt.datetime.now()
        self.databaseChecked = False

    def checkDatabase(self):
        if self.database.initDatabase() == -1:
            self.log.info("Could not reach database, check your network")
            self.quit()
        else:
            self.log.info("Database OK")
            self.databaseChecked = True

    @botcmd
    def subscribe(self, mess, args):
        """Subscribe to the broadcast list"""
        user = mess.getFrom()
        if user in self.users_subscribe:
            return 'You are already subscribed.'
        else:
            self.users_subscribe.append(user)
            with open(self.path + 'list_subscribe', 'w') as fichier:
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
            with open(self.path + 'list_subscribe', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.users_subscribe)
            self.log.info('%s unsubscribed from the broadcast.' % user)
            return 'You are now unsubscribed.'

    @botcmd
    def alarm_on(self, mess, args):
        """Be noticed by the alarms"""
        new_user = mess.getFrom()
        if new_user not in self.users_alarm:
            self.users_alarm.append(new_user)
            with open(self.path + 'list_alarm', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.users_alarm)
            return "You are on Alarm MODE !"
        else:
            return "Stop harassing me please !"

    @botcmd
    def alarm_off(self, mess, args):
        """Ignore the alarms"""
        user = mess.getFrom()
        if user in self.users_alarm:
            self.users_alarm.remove(user)
            with open(self.path + 'list_alarm', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.users_alarm)
            return "You aren't on alarm MODE anymore !"

        else:
            return "Are you kidding me !?"

    @botcmd
    def pressure(self, mess=None, args=None):
        """Get pressure from gauge"""
        pressure_date, [pressure_val] = self.database.getLastData(self.actor.lower() + "pressure", "val1")
        val_mbar = 1.33322368 * pressure_val

        return pressure_date + "\n Pressure (Torr) =%.3e" % pressure_val + "\n Pressure (mBar) = %.3e " % val_mbar

    @botcmd
    def turbo(self, mess=None, args=None):
        """Get turbo parameters"""
        turbospeed_date, [turbospeed_val] = self.database.getLastData(self.actor.lower() + "turbospeed", "val1")
        turbo_date, [turbo_bodytemp, turbo_controllertemp] = self.database.getLastData(
            self.actor.lower() + "turboTemps", "bodytemp, controllertemp")

        return turbospeed_date + "\n Turbo Speed(RPM) = %i\n Body Temp(\xe2\x84\x83) = %0.1f\n Controller Temp(\xe2\x84\x83) = %0.1f" % (
            turbospeed_val, turbo_bodytemp, turbo_controllertemp)

    @botcmd
    def temperature(self, mess=None, args=None):
        """Get data from temperatures sensor"""
        temps_date, [detect_box, mangin, rod_a, therm_spreader_assy, roc_c, detect_therm_assy1,
                     detect_therm_assy2] = self.database.getLastData(self.actor.lower() + "temps",
                                                                     "val1_0, val1_1, val1_2, val1_3, val1_4, val1_10, val1_11")

        return temps_date + "\n Thermal Spreader Assy(K) = %0.2f\n Rod C(K) = %0.2f\n  Rod A(K) = %0.2f\n Detector Box(K) = %0.2f\n Detector Strap 1(K) = %0.2f\n Detector Strap 2(K) = %0.2f\n Mangin(K) = %0.2f" % (
            therm_spreader_assy, roc_c, rod_a, detect_box, detect_therm_assy1, detect_therm_assy2, mangin,)

    @botcmd
    def lam_temps(self, mess=None, args=None):
        """Get data from LAM temperatures sensor"""
        temps_date, [preamp_board, det_spider_c_in, cold_strap_c_out, cold_strap_c_in, thermal_bar_c, detect_box,
                     detect_plate, detect_spider_c_out] = self.database.getLastData("vistherm__lamtemps1",
                                                                                    "val1_0, val1_1, val1_2, val1_3, val1_4, val1_5, val1_6, val1_7")
        temps_date, [rod_shield_c, tip, detect_actuator, red_tube, corrector_cell, cover_detect, thermal_spreader,
                     cover_rod_c_up, cover_rod_c_down] = self.database.getLastData("vistherm__lamtemps2",
                                                                                   "val1_0, val1_1, val1_2, val1_3, val1_4, val1_5, val1_6, val1_7, val1_8")

        return temps_date + "\n Tip(K) = %0.2f\n Thermal Spreader(K) = %0.2f\n Thermal Bar C(K) = %0.2f\n Cold Strap C IN(K) = %0.2f\n Cold Strap C OUT(K) = %0.2f\n Detect Spider C IN(K) = %0.2f\n Detect Spider C OUT(K) = %0.2f\n Detector Box(K) = %0.2f\n Detector Plate(K) = %0.2f\n Preamp Board(K) = %0.2f\n Cover Detector(K) = %0.2f\n Cover Rod C DOWN(K) = %0.2f\n Cover Rod C UP(K) = %0.2f\n Rod Shield C(K) = %0.2f\n Detect Actuator(K) = %0.2f\n Red Tube(K) = %0.2f\n Corrector Cell(K) = %0.2f" % \
                            (tip, thermal_spreader, thermal_bar_c, cold_strap_c_in, cold_strap_c_out, det_spider_c_in,
                             detect_spider_c_out, detect_box, detect_plate, preamp_board, cover_detect,
                             cover_rod_c_down, cover_rod_c_up, rod_shield_c, detect_actuator, red_tube, corrector_cell)

    @botcmd
    def cooler(self, mess=None, args=None):
        """Get Cryocooler parameters"""
        cooler_date, [cooler_setpoint, cooler_reject, cooler_tip, cooler_power] = self.database.getLastData(
            self.actor.lower() + "coolertemps", "setpoint, reject, tip, power")

        return cooler_date + "\n Set Point(K) = %i\n Reject(\xe2\x84\x83) = %0.2f\n Collar(K) = %0.2f\n Power(W)= %0.1f" % (
            cooler_setpoint, cooler_reject, cooler_tip, cooler_power)

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
    def alarm_ack(self, mess, args):
        """Alarm acknowledgement, arguments : pressure|turbo|gatevalve|cooler """
        if args.lower() in ["turbo", "cooler", "pressure", "gatevalve"]:
            self.alarm_ack[args.lower()] = True
            with open(self.path + 'alarm_ack', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.alarm_ack)
            for user in self.users_alarm:
                self.send(user, "Alarm %s acknowledge by %s  on %s" % (
                    args.lower(), str(mess.getFrom().getNode()),
                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        else:
            return "no such device"

    @botcmd
    def alarm_rearm(self, mess, args):
        """Alarm rearmament, arguments : pressure|turbo|gatevalve|cooler """
        if args.lower() in ["turbo", "cooler", "pressure", "gatevalve"]:
            self.alarm_ack[args.lower()] = False
            with open(self.path + 'alarm_ack', 'w') as fichier:
                mon_pickler = pickle.Pickler(fichier)
                mon_pickler.dump(self.alarm_ack)
            for user in self.users_alarm:
                self.send(user, "Alarm %s rearmed by %s  on %s" % (
                    args.lower(), str(mess.getFrom().getNode()),
                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        else:
            return "no such device"

    @botcmd
    def all(self, mess, args):
        """Get all parameters """
        user = mess.getFrom()
        res = ""
        res += "%s\n" % self.turbo()
        res += "\n%s\n" % self.pressure()
        res += "\n%s\n" % self.cooler()
        res += "\n%s\n" % self.temperature()
        res += "\n%s" % self.lam_temps()
        self.send(user, res)

    @botcmd(hidden=True)
    def reboot_bot(self, mess, args):
        """reboot bot """
        self.parent.rebootBot()

    @botcmd(hidden=True)
    def curious_guy(self, mess, args):
        """WHO Suscribe to the alarm"""
        txt = "%s\n %s\n %s\n" % (','.join([str(user.getNode()) for user in self.users_alarm]),
                                  ','.join([str(user.getNode()) for user in self.users_subscribe]), str(self.alarm_ack))

        return txt

    def checkCriticalValue(self):

        pressure_date, [pressure_val] = self.database.getLastData(self.actor.lower() + "pressure", "val1")
        turbospeed_date, [turbospeed_val] = self.database.getLastData(self.actor.lower() + "turbospeed", "val1")
        gatevalve_date, [gatevalve_val] = self.database.getLastData(self.actor.lower() + "gatevalve", "val1")
        coolerPower_date, [coolerPower_val] = self.database.getLastData(self.actor.lower() + "coolertemps", "power")

        if float(pressure_val) > 1e-4:
            message = " WARNING    Pressure :  %s  (Torr)   on    %s" % ('{:.3e}'.format(pressure_val), pressure_date)
            if self.alarm_ack["pressure"] == False:
                for user in self.users_alarm:
                    self.send(user, message)

        if turbospeed_val < 90000:
            message = "WARNING    Turbo Speed : %s  (RPM) on   %s" % (str(turbospeed_val), turbospeed_date)
            if self.alarm_ack["turbo"] == False:
                for user in self.users_alarm:
                    self.send(user, message)

        if gatevalve_val != 253:
            message = "WARNING    GateValve not OPENED anymore !  on    %s" % (gatevalve_date)
            if self.alarm_ack["gatevalve"] == False:
                for user in self.users_alarm:
                    self.send(user, message)

        if not 70 < coolerPower_val < 265:
            message = "WARNING    Cooler Power : %s  (W)  on    %s" % (str(coolerPower_val), coolerPower_date)
            if self.alarm_ack["cooler"] == False:
                for user in self.users_alarm:
                    self.send(user, message)

    def idle_proc(self):
        if not self.databaseChecked:
            self.checkDatabase()
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
        if self.databaseChecked:
            self.checkCriticalValue()
            if (dt.datetime.now() - self.t0).total_seconds() > 3600:
                turbo_text = self.turbo()
                self.message_queue.append(turbo_text)
                pressure_text = self.pressure()
                self.message_queue.append(pressure_text)
                cooler_text = self.cooler()
                self.message_queue.append(cooler_text)
                temps_text = self.temperature()
                self.message_queue.append(temps_text)
                self.t0 = dt.datetime.now()


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
            time.sleep(300)
        self.nb_bot.append(
            BroadcastingJabberBot(self.jid, self.password, self, self.ip, self.port, self.path,
                                  self.getuseralarm(), self.getuserSubscribe(), self.getalarmAck(), kill_old))
        self.nb_th.append(StoppableThread(self.nb_bot[-1]))
        self.nb_bot[-1].serve_forever(connect_callback=lambda: self.nb_th[-1].start(),
                                      disconnect_callback=lambda: self.rebootBot())

    def deleteBot(self):
        self.nb_bot[-1].log.info("%s   Deleting bot" % dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        self.nb_bot[-1].quit()
        self.nb_th[-1].join()
        del (self.nb_bot[-1])
        del (self.nb_th[-1])

    def rebootBot(self):
        self.initialize_new_bot(kill_old=True, )

    def getuseralarm(self):
        with open(self.path + 'list_alarm', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()

    def getuserSubscribe(self):
        with open(self.path + 'list_subscribe', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()

    def getalarmAck(self):
        with open(self.path + 'alarm_ack', 'r') as fichier:
            mon_depickler = pickle.Unpickler(fichier)
            return mon_depickler.load()
