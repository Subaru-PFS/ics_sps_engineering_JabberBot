import pickle
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename

import numpy as np
from Crypto.Cipher import AES
from ics_sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager
from matplotlib.dates import num2date

colors = ['#1f78c5', '#ff801e', '#2ca13c', '#d82738', '#9568cf', '#8d565b', '#e578c3', '#17bfd1', '#808080',
          '#caca76', '#000000', '#acc5f5', '#fcb986', '#96dc98', '#fc96a4', '#c3aee2', '#c29aa2', '#f4b4cf',
          '#9cd7e2', '#fdff43', '#c5c5c5']


class Data(object):
    def __init__(self, tstamp, vals, label, col):
        object.__init__(self)
        self.tstamp = tstamp
        self.vals = vals
        self.label = label
        self.col = col

    @property
    def props(self):
        return self.tstamp, self.vals, self.label, self.col


def exportData(pfsbot, dates, rm):
    db = DatabaseManager(pfsbot.db_addr, pfsbot.db_port)
    db.initDatabase()

    plot1, col1 = [], 0
    plot2, col2 = [], 0
    plot3, col3 = [], 0
    plot4, col4 = [], 0

    rm.extend(['Pt%i' % i for i in range(12)])

    allc1 = [("xcu_%s__pressure" % pfsbot.cam, "val1"),
             ("xcu_%s__ionpump1" % pfsbot.cam, "pressure"),
             ("xcu_%s__ionpump2" % pfsbot.cam, "pressure"),
             ]

    allc2 = [("xcu_%s__coolertemps" % pfsbot.cam, "tip"),
             ("ccd_%s__ccdtemps" % pfsbot.cam, "ccd0", "CCD_Temp0"),
             ("ccd_%s__ccdtemps" % pfsbot.cam, "ccd1", "CCD_Temp1"),
             ("aitroom__weatherduino", "temp", "Room_Temp")]

    allc2.extend([("xcu_%s__temps" % pfsbot.cam, "val1_%i" % i) for i in range(12)])
    allc2.extend([("vistherm__lamtemps1", "val1_%i" % i) for i in range(8)])
    allc2.extend([("vistherm__lamtemps2", "val1_%i" % i) for i in range(9)])
    allc2.extend([("aitenv__aitenv", "val1_%i" % i) for i in range(2)])

    allc3 = [("xcu_%s__coolertemps" % pfsbot.cam, "power", "Cooler_Power")]

    for allc in [allc1, allc2, allc3]:
        for i, elem in enumerate(allc):
            vkeys = ','.join([k for k in elem[1].split(',')
                              if '%s-%s' % (elem[0], k) in pfsbot.curveDict.iterkeys()])

            allc[i] = (elem[0], vkeys, ',' * len(elem[1].split(','))) if len(elem) == 2 \
                                                                      else (elem[0], vkeys, elem[2])

    allc1 = [curve for curve in allc1 if curve[1]]
    allc2 = [curve for curve in allc2 if curve[1]]
    allc3 = [curve for curve in allc3 if curve[1]]

    for table, keys, hardLabels in allc1:
        try:
            tstamp, vals = db.getDataBetween(table, keys, *dates)
            for i, (key, hardLabel) in enumerate(zip(keys.split(','), hardLabels.split(','))):
                device, typ, label = pfsbot.curveDict['%s-%s' % (table, key)]
                label = hardLabel if hardLabel else label
                vals = checkValues(vals[:, i], typ)
                if label not in rm:
                    plot1.append(Data(tstamp, vals, '%s' % device, colors[col1]))
                    col1 += 1

        except Exception as e:
            print e
            print table, keys, hardLabels

    for table, keys, hardLabels in allc2:
        try:
            tstamp, vals = db.getDataBetween(table, keys, *dates)

            for i, (key, hardLabel) in enumerate(zip(keys.split(','), hardLabels.split(','))):
                device, typ, label = pfsbot.curveDict['%s-%s' % (table, key)]
                label = hardLabel if hardLabel else label
                vals = checkValues(vals[:, i], typ)
                if label not in rm:
                    offset = 273.15 if typ == 'temperature_c' else 0
                    vals += offset
                    if np.mean(vals) < 270:
                        label = checkLabel(plot2, label)
                        plot2.append(Data(tstamp, vals, '%s' % label, colors[col2]))
                        col2 += 1
                    else:
                        label = checkLabel(plot4, label)
                        plot4.append(Data(tstamp, vals, '%s' % label, colors[col4]))
                        col4 += 1

        except Exception as e:
            print e
            print table, keys, hardLabels

    for table, keys, hardLabels in allc3:
        try:
            tstamp, vals = db.getDataBetween(table, keys, *dates)

            for i, (key, hardLabel) in enumerate(zip(keys.split(','), hardLabels.split(','))):
                device, typ, label = pfsbot.curveDict['%s-%s' % (table, key)]
                label = hardLabel if hardLabel else label
                if label not in rm:
                    vals = checkValues(vals[:, i], typ)
                    plot3.append(Data(tstamp, vals, '%s' % label, colors[col2]))

        except Exception as e:
            print e
            print table, keys, hardLabels

    db.closeDatabase()

    return plot1, plot2, plot3, plot4


def checkValues(values, type):
    allMin = {'temperature_k': 15, "pressure_torr": 1e-9, "power": 0, "temperature_c": -20}
    allMax = {'temperature_k': 349, "pressure_torr": 1e4, "power": 250, "temperature_c": 60}
    minVal = allMin[type]
    maxVal = allMax[type]

    ind = np.logical_and(values >= minVal, values <= maxVal)
    values[~ind] = np.nan

    return values


def checkLabel(plot, label):
    found = False
    labels = [data.label for data in plot]
    if label in labels:
        label = "AIT_%s" % label

    return label


def fmtDate(date, fmt="%Y-%m-%dT%H:%M:%S"):
    return num2date(date).strftime(fmt)


def send_file(send_to, myfile, subject):
    send_from = 'arnaud.lefur@lam.fr'
    text = 'This email has been generated for PFS AIT'
    server = "smtp.osupytheas.fr"
    port = 587
    with open('/home/pfs/AIT-PFS/current/word.txt', 'r') as thisFile:
        unpickler = pickle.Unpickler(thisFile)
        pf1, pf2 = unpickler.load()

    decryption_suite = AES.new(pf1, AES.MODE_CBC, pf2)
    user = decryption_suite.decrypt('b\xb5\xcb\x8b%\xd1\n\x80R\xf6\xb3\x1e\xe6}\xad\x0e').strip()
    password = decryption_suite.decrypt('!E\x83\xd73%\xeaS\xe8&\xa6\x11\xd6\x0b\xf4r').strip()

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
