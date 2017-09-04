import ConfigParser
import os
import smtplib
from datetime import datetime as dt
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename
from threading import Thread

import numpy as np
import pandas as pd
from ics_sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager
from matplotlib.dates import num2date


class Expdata(Thread):
    def __init__(self, pfsbot, user, dstart, dend, step):
        Thread.__init__(self)
        self.pfsbot = pfsbot
        self.user = user
        self.curveDict = {}
        self.db = DatabaseManager(pfsbot.db_addr, pfsbot.db_port)
        self.db.initDatabase()
        self.dstart = dstart
        self.dend = dend
        self.step = step

    def run(self):
        self.readCfg(self.pfsbot.config_path)
        fname = self.extractData()

        address = self.pfsbot.knownUsers[self.user.getNode()]
        self.send_pdf(address, fname)
        self.pfsbot.send(self.user, "I've just sent the data to %s" % address)

        self.db.closeDatabase()

        return

    def readCfg(self, path):
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
        config = ConfigParser.ConfigParser()

        res2 = []
        for f, datetime in res:
            if self.dstart > datetime:
                res2.append((f, self.dstart - datetime))
        if res2:
            res2.sort(key=lambda tup: tup[1])
            config.readfp(open(path + res2[0][0]))
        else:
            res.sort(key=lambda tup: tup[1])
            config.readfp(open(path + res[0][0]))

        for a in config.sections():
            if a != 'config_date':
                tableName = a
                fname = config.get(a, "bot_cmd")
                key = config.get(a, 'key')
                label = config.get(a, 'label')
                unit = config.get(a, 'unit')
                labelDevice = config.get(a, 'label_device')
                if self.pfsbot.isRelevant(tableName):
                    for k, l, t in zip([k.strip() for k in key.split(',')],
                                       [l.strip() for l in label.split(',')],
                                       [t.strip() for t in config.get(a, 'type').split(',')]):
                        self.curveDict["%s-%s" % (tableName, k)] = labelDevice, t, l

    def extractData(self):
        plot1 = []
        plot2 = []
        plot3 = []
        plot4 = []

        careless = ['Red Tube2'] + ['Pt%i' % i for i in range(12)]

        allc1 = [("xcu_%s__pressure" % self.pfsbot.cam, "val1"),
                 ("xcu_%s__ionpump1" % self.pfsbot.cam, "pressure"),
                 ("xcu_%s__ionpump2" % self.pfsbot.cam, "pressure"),
                 ]

        allc2 = [("xcu_%s__coolertemps" % self.pfsbot.cam, "tip"),
                 ("ccd_%s__ccdtemps" % self.pfsbot.cam, "ccd0"),
                 ("ccd_%s__ccdtemps" % self.pfsbot.cam, "ccd1"),
                 ("aitroom__weatherduino", "temp", "Room_Temp")]

        allc2.extend([("xcu_%s__temps" % self.pfsbot.cam, "val1_%i" % i) for i in range(12)])
        allc2.extend([("vistherm__lamtemps1", "val1_%i" % i) for i in range(8)])
        allc2.extend([("vistherm__lamtemps2", "val1_%i" % i) for i in range(9)])
        allc2.extend([("aitenv__aitenv", "val1_%i" % i) for i in range(2)])

        allc3 = [("xcu_%s__coolertemps" % self.pfsbot.cam, "power", "Cooler_Power")]

        for allc in [allc1, allc2, allc3]:
            for i, elem in enumerate(allc):
                vkeys = ','.join(
                    [k for k in elem[1].split(',') if '%s-%s' % (elem[0], k) in self.curveDict.iterkeys()])

                allc[i] = (elem[0], vkeys, ',' * len(elem[1].split(','))) if len(elem) == 2 else (
                    elem[0], vkeys, elem[2])

        allc1 = [curve for curve in allc1 if curve[1]]
        allc2 = [curve for curve in allc2 if curve[1]]
        allc3 = [curve for curve in allc3 if curve[1]]

        for table, keys, hardLabels in allc1:
            tstamp, vals = self.db.getDataBetween(table, keys,
                                                  self.dstart.strftime("%d/%m/%Y %H:%M:%S"),
                                                  self.dend.strftime("%d/%m/%Y %H:%M:%S"))

            try:
                for i, (key, hardLabel) in enumerate(zip(keys.split(','), hardLabels.split(','))):
                    device, typ, label = self.curveDict['%s-%s' % (table, key)]
                    label = hardLabel if hardLabel else label
                    vals = self.checkValues(vals[:, i], typ)
                    plot1.append((tstamp, vals, '%s' % device))

            except Exception as e:
                print e

        for table, keys, hardLabels in allc2:
            tstamp, vals = self.db.getDataBetween(table, keys,
                                                  self.dstart.strftime("%d/%m/%Y %H:%M:%S"),
                                                  self.dend.strftime("%d/%m/%Y %H:%M:%S"))

            try:
                for i, (key, hardLabel) in enumerate(zip(keys.split(','), hardLabels.split(','))):
                    device, typ, label = self.curveDict['%s-%s' % (table, key)]
                    label = hardLabel if hardLabel else label
                    vals = self.checkValues(vals[:, i], typ)
                    if label not in careless:
                        offset = 273.15 if typ == 'temperature_c' else 0
                        vals += offset
                        if np.mean(vals) < 270:
                            label = self.checkLabel(plot2, label)
                            plot2.append((tstamp, vals, '%s' % label))

                        else:
                            label = self.checkLabel(plot4, label)
                            plot4.append((tstamp, vals, '%s' % label))


            except Exception as e:
                print e

        for table, keys, hardLabels in allc3:
            tstamp, vals = self.db.getDataBetween(table, keys,
                                                  self.dstart.strftime("%d/%m/%Y %H:%M:%S"),
                                                  self.dend.strftime("%d/%m/%Y %H:%M:%S"))

            try:
                for i, (key, hardLabel) in enumerate(zip(keys.split(','), hardLabels.split(','))):
                    device, typ, label = self.curveDict['%s-%s' % (table, key)]
                    label = hardLabel if hardLabel else label
                    vals = self.checkValues(vals[:, i], typ)
                    plot3.append((tstamp, vals, '%s' % label))

            except Exception as e:
                print e

        plots = plot1 + plot2 + plot3 + plot4
        samp_start = np.max([tstamp[0] for tstamp, vals, label in plots])
        samp_end = np.min([tstamp[-1] for tstamp, vals, label in plots])
        step = self.step * 1.1574073384205501e-5

        ti = np.arange(samp_start, samp_end, step)

        datas = {'Time': [self.fmtDate(t) for t in ti]}

        for tstamp, vals, label in plots:
            datas[label] = np.interp(ti, tstamp, vals)

        df = pd.DataFrame.from_dict(datas)
        df = df.set_index('Time')

        fname = '/home/alefur/AIT-PFS/jabberLog/PFS_Data-%s_%s.csv' % (self.pfsbot.cam.upper(),
                                                                       self.fmtDate(ti[0], "%Y-%m-%d"))

        df.to_csv(fname)

        return fname

    def checkValues(self, values, type):
        allMin = {'temperature_k': 15, "pressure_torr": 1e-9, "power": 0, "temperature_c": -20}
        allMax = {'temperature_k': 349, "pressure_torr": 1e4, "power": 250, "temperature_c": 60}
        minVal = allMin[type]
        maxVal = allMax[type]

        ind = np.logical_and(values >= minVal, values <= maxVal)
        values[~ind] = np.nan

        return values

    def checkLabel(self, plot, label):
        found = False
        labels = [lab for (tstamp, vals, lab) in plot]
        if label in labels:
            label = "AIT_%s" % label

        return label

    def send_pdf(self, send_to, myfile):

        send_from = 'arnaud.lefur@lam.fr'
        subject = '[PFS] AIT Data'
        text = 'This email has been generated for PFS AIT'
        server = "smtp.osupytheas.fr"
        port = 587
        user = "alefur"
        password = "cia2757cfc"
        msg = MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = COMMASPACE.join([send_to])
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach(MIMEText(text))

        with open(myfile, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(myfile)
            )
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(myfile)
            msg.attach(part)

        smtp = smtplib.SMTP(server, port)
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(send_from, [send_to], msg.as_string())
        smtp.close()

    def fmtDate(self, date, fmt="%Y-%m-%dT%H:%M:%S"):
        return num2date(date).strftime(fmt)
