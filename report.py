import matplotlib as mpl

mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages

import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from threading import Thread
from ics_sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager

from datetime import datetime as dt


class Report(Thread):
    colors = ['#1f78c5', '#ff801e', '#2ca13c', '#d82738', '#9568cf', '#8d565b', '#e578c3', '#17bfd1', '#f2f410',
              '#808080', '#000000', '#acc5f5', '#fcb986', '#96dc98', '#fc96a4', '#c3aee2', '#c29aa2', '#f4b4cf',
              '#9cd7e2', '#caca76', '#c5c5c5']

    def __init__(self, pfsbot, timedelta, user):

        Thread.__init__(self)

        t0 = dt.now()
        str_date = (t0 - timedelta).strftime("%d/%m/%Y %H:%M:%S")

        self.str_date = str_date
        self.pfsbot = pfsbot
        self.user = user

        self.db = DatabaseManager(pfsbot.db_addr, pfsbot.db_port)
        self.db.initDatabase()

    def run(self):
        file_name = self.generate_pdf(self.db, self.str_date)
        if file_name:
            address = self.pfsbot.knownUsers[self.user.getNode()]
            self.send_pdf(address, file_name)
            self.pfsbot.send(self.user, "I've just sent the report to %s" % address)
        else:
            self.pfsbot.send(self.user, "an error has occured")
        self.db.closeDatabase()
        return

    def generate_pdf(self, db, str_date):

        plot1, col1 = [], 0
        plot2, col2 = [], 0
        plot3, col3 = [], 0
        plot4, col4 = [], 0

        fig1 = None
        fig2 = None
        fig3 = None

        careless = ['Field Lens', 'Red Tube2'] + ['Pt%i' % i for i in range(12)]

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

        allc3 = [("xcu_%s__coolertemps" % self.pfsbot.cam, "power")]

        for allc in [allc1, allc2, allc3]:
            for i, elem in enumerate(allc):
                vkeys = ','.join(
                    [k for k in elem[1].split(',') if '%s-%s' % (elem[0], k) in self.pfsbot.curveDict.iterkeys()])

                allc[i] = (elem[0], vkeys, None) if len(elem) == 2 else (elem[0], vkeys, elem[1])

        allc1 = [curve for curve in allc1 if curve[1]]
        allc2 = [curve for curve in allc2 if curve[1]]
        allc3 = [curve for curve in allc3 if curve[1]]

        for table, keys, hardLabel in allc1:
            tstamp, vals = db.getDataBetween(table, keys, str_date)

            try:
                for i, key in enumerate(keys.split(',')):
                    device, typ, label = self.pfsbot.curveDict['%s-%s' % (table, key)]
                    label = hardLabel if hardLabel is not None else label
                    vals = self.checkValues(vals[:, i], typ)
                    plot1.append((tstamp, vals, '%s' % device, Report.colors[col1]))
                    col1 += 1

            except Exception as e:
                print e

        for table, keys, hardLabel in allc2:
            tstamp, vals = db.getDataBetween(table, keys, str_date)

            try:
                for i, key in enumerate(keys.split(',')):
                    device, typ, label = self.pfsbot.curveDict['%s-%s' % (table, key)]
                    label = hardLabel if hardLabel is not None else label
                    vals = self.checkValues(vals[:, i], typ)
                    if label not in careless:
                        offset = 273.15 if typ == 'temperature_c' else 0
                        vals += offset
                        if np.mean(vals) < 270:
                            label = self.checkLabel(plot2, label)
                            plot2.append((tstamp, vals, '%s' % label, Report.colors[col2]))
                            col2 += 1
                        else:
                            label = self.checkLabel(plot4, label)
                            plot4.append((tstamp, vals, '%s' % label, Report.colors[col4]))
                            col4 += 1

            except Exception as e:
                print e

        for table, keys, hardLabel in allc3:
            tstamp, vals = db.getDataBetween(table, keys, str_date)

            try:
                for i, key in enumerate(keys.split(',')):
                    device, typ, label = self.pfsbot.curveDict['%s-%s' % (table, key)]
                    label = hardLabel if hardLabel is not None else label
                    vals = self.checkValues(vals[:, i], typ)
                    plot3.append((tstamp, vals, '%s' % device, Report.colors[col2]))

            except Exception as e:
                print e

        if plot1:
            fig1 = plt.figure()
            ax1 = fig1.add_subplot(111)

            for date, values, label, col in plot1:
                ax1.plot_date(date, values, '-', label=label, color=col)

            ax1.set_yscale('log', basey=10)
            subs = [1.0, 2.0, 3.0, 5.0]  # ticks to show per decade
            ax1.yaxis.set_minor_locator(ticker.LogLocator(subs=subs))  # set the ticks position
            minor_locatorx = ticker.AutoMinorLocator(5)
            ax1.xaxis.set_minor_locator(minor_locatorx)
            ax1.set_ylabel("Pressure (Torr)", color=Report.colors[0])
            for tick in ax1.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(Report.colors[0])
                ax1.grid(which='major', alpha=0.5, color=Report.colors[0])
                ax1.grid(which='minor', alpha=0.25, color=Report.colors[0])
            box = ax1.get_position()
            ax1.set_position([box.x0, 0.18, box.width, box.height * 0.8])
            lns, labs = self.sortCurve([ax1])
            ax1.legend(lns, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=3, mode="expand", borderaxespad=0.,
                       prop={'size': 11})
            ax1.xaxis.set_major_formatter(DateFormatter(self.getDateFormat(ax1.get_xlim())))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=75, horizontalalignment='right')

        if plot2:
            fig2 = plt.figure()
            ax2 = fig2.add_subplot(111)
            ax3 = ax2.twinx()

            for date, values, label, col in plot2:
                ax2.plot_date(date, values, '-', label=label, color=col)
            if plot3:
                for date, values, label, col in plot3:
                    ax3.plot_date(date, values, '-', label=label, color=col)

            ax2.set_ylabel("Temperature (K)", color=Report.colors[0])
            for tick in ax2.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(color=Report.colors[0])
                ax3.grid(which='major', alpha=0.0)
                ax2.grid(which='major', alpha=0.5, color=Report.colors[0])
                ax2.grid(which='minor', alpha=0.25, color=Report.colors[0], linestyle='--')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax2.yaxis.set_minor_locator(minor_locatory)
            ax2.get_yaxis().get_major_formatter().set_useOffset(False)

            ax3.set_ylabel("Power (W)", color=col)
            for tick in ax3.yaxis.get_major_ticks():
                tick.label1On = False
                tick.label2On = True
                tick.label2.set_color(color=col)
                ax3.grid(which='major', alpha=1.0, color=col, linestyle='dashdot')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax3.yaxis.set_minor_locator(minor_locatory)
            ax3.get_yaxis().get_major_formatter().set_useOffset(False)

            box = ax2.get_position()
            ax2.set_position([box.x0, 0.18, box.width, box.height * 0.8])
            ax3.set_position([box.x0, 0.18, box.width, box.height * 0.8])

            lns, labs = self.sortCurve([ax2, ax3])
            ax2.legend(lns, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=4, mode="expand", borderaxespad=0.,
                       prop={'size': 9})
            ax2.xaxis.set_major_formatter(DateFormatter(self.getDateFormat(ax2.get_xlim())))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=75, horizontalalignment='right')

        if plot4:

            fig3 = plt.figure()
            ax4 = fig3.add_subplot(111)
            ax5 = ax4.twinx()

            for date, values, label, col in plot4:
                ax4.plot_date(date, values, '-', label=label, color=col)

            ax4.set_ylabel("Temperature (K)", color=Report.colors[0])
            for tick in ax4.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(color=Report.colors[0])
                ax4.grid(which='major', alpha=0.5, color=Report.colors[0])
                ax4.grid(which='minor', alpha=0.25, color=Report.colors[0], linestyle='--')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax4.yaxis.set_minor_locator(minor_locatory)
            ax4.get_yaxis().get_major_formatter().set_useOffset(False)

            ax5.set_ylabel("Temperature (C)", color=Report.colors[10])
            for tick in ax5.yaxis.get_major_ticks():
                tick.label1On = False
                tick.label2On = True
                tick.label2.set_color(color=Report.colors[10])
                ax5.grid(which='major', alpha=1.0, color=Report.colors[10], linestyle='dashdot')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax5.yaxis.set_minor_locator(minor_locatory)
            ax5.get_yaxis().get_major_formatter().set_useOffset(False)

            box = ax4.get_position()
            ax4.set_position([box.x0, 0.18, box.width, box.height * 0.8])
            ax5.set_position([box.x0, 0.18, box.width, box.height * 0.8])

            lns, labs = self.sortCurve([ax4])
            ax4.legend(lns, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=4, mode="expand", borderaxespad=0.,
                       prop={'size': 8})
            ax5.set_ylim((ax4.get_ylim()[0] - 273.15, ax4.get_ylim()[1] - 273.15))

            ax4.xaxis.set_major_formatter(DateFormatter(self.getDateFormat(ax4.get_xlim())))
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=75, horizontalalignment='right')

        file_name = '/home/pfs/AIT-PFS/jabberLog/PFS_AIT_Report-%s_%s.pdf' % (self.pfsbot.cam.upper(),
                                                                              dt.now().strftime("%Y-%m-%d_%H-%M"))

        if fig1 is not None or fig2 is not None or fig3 is not None:
            with PdfPages(file_name) as pdf:
                if fig1 is not None:
                    pdf.savefig(fig1)
                    plt.close()

                if fig2 is not None:
                    pdf.savefig(fig2)
                    plt.close()

                if fig3 is not None:
                    pdf.savefig(fig3)
                    plt.close()

            return file_name
        else:
            return None

    def getDateFormat(self, (t0, tmax)):

        if tmax - t0 > 7:
            format_date = "%d/%m/%Y"
        elif tmax - t0 > 1:
            format_date = "%a %H:%M"
        else:
            format_date = "%H:%M:%S"
        return format_date

    def checkValues(self, values, type):
        allMin = {'temperature_k': 15, "pressure_torr": 1e-9, "power": 0, "temperature_c": -20}
        allMax = {'temperature_k': 349, "pressure_torr": 1e4, "power": 250, "temperature_c": 60}
        minVal = allMin[type]
        maxVal = allMax[type]

        ind = np.logical_and(values >= minVal, values <= maxVal)
        values[~ind] = np.nan

        return values

    def sortCurve(self, list_axes):
        vmax = []
        lns = []
        labs = []
        for ax in list_axes:
            for line in ax.get_lines():
                vmax.append([line.get_ydata()[-1], line.get_label(), line])

        vmax.sort(key=lambda row: row[0])
        for [v, labels, lines] in reversed(vmax):
            lns.append(lines)
            labs.append(labels)

        return lns, labs

    def checkLabel(self, plot, label):
        found = False
        labels = [lab for (tstamp, vals, lab, color) in plot]
        if label in labels:
            label = "AIT_%s" % label

        return label

    def send_pdf(self, send_to, myfile):

        send_from = 'arnaud.lefur@lam.fr'
        subject = '[PFS] AIT Report'
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
