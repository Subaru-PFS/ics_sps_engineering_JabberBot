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
    color = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
             (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
             (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
             (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
             (188, 189, 34), (224, 198, 17), (23, 190, 207), (158, 218, 229)]

    for i, colors in enumerate(color):
        r, g, b = colors
        color[i] = (r / 255., g / 255., b / 255.)

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
        plot1 = []
        plot2 = []
        plot3 = []
        plot4 = []
        fig1 = None
        fig2 = None
        fig3 = None
        t0 = dt.now()
        # try:
        #     visthermGauge_date, visthermGauge_val = db.getDataBetween("vistherm__gauge", "secondary", str_date)
        #     visthermGauge_val = self.checkValues(visthermGauge_val, ["pressure"] * 1)
        #     plot1.append((visthermGauge_date, visthermGauge_val[:, 0], 'LAM_Gauge', Report.color[0]))
        # except:
        #     pass
        try:
            ionGauge_date, ionGauge_val = db.getDataBetween("xcu_r1__pressure", "val1", str_date)
            ionGauge_val = self.checkValues(ionGauge_val, ['pressure'])
            plot1.append((ionGauge_date, ionGauge_val[:, 0], 'Ion_Gauge', Report.color[2]))
        except:
            pass
        try:
            frontGauge_date, frontGauge_val = db.getDataBetween("xcu_r1__roughpressure1", "val1", str_date)
            frontGauge_val = self.checkValues(frontGauge_val, ['pressure'])
            plot1.append((frontGauge_date, frontGauge_val[:, 0], 'Roughing_Gauge', Report.color[4]))
        except:
            pass
        try:
            xcuIon3_date, xcuIon3_val = db.getDataBetween("xcu_r1__ionpump1", "pressure", str_date)
            xcuIon4_date, xcuIon4_val = db.getDataBetween("xcu_r1__ionpump2", "pressure", str_date)
            xcuIon3_val = self.checkValues(xcuIon3_val, ["pressure"] * 1)
            xcuIon4_val = self.checkValues(xcuIon4_val, ["pressure"] * 1)
            plot1.extend([(xcuIon3_date, xcuIon3_val[:, 0], 'Ionpump1', Report.color[10]),
                          (xcuIon4_date, xcuIon4_val[:, 0], 'Ionpump2', Report.color[12])])
        except:
            pass

        try:
            cooler_date, cooler_val = db.getDataBetween("xcu_r1__coolertemps", "tip, power", str_date)
            cooler_val = self.checkValues(cooler_val, ["temp_k", "power"])
            plot2.append((cooler_date, cooler_val[:, 0], 'Cooler_Collar', Report.color[0]))
            plot3.append((cooler_date, cooler_val[:, 1], 'Cooler_Power', Report.color[10]))

        except:
            pass
        try:

            xcuTemps_date, xcuTemps_val = db.getDataBetween("xcu_r1__temps",
                                                            "val1_0, val1_1, val1_3, val1_4, val1_10, val1_11",
                                                            str_date)
            xcuTemps_val = self.checkValues(xcuTemps_val, ["temp_k"] * 6)
            plot2.extend([(xcuTemps_date, xcuTemps_val[:, 2], 'Spreader', Report.color[1]),
                          (xcuTemps_date, xcuTemps_val[:, 0], 'Detector Box', Report.color[8]),
                          (xcuTemps_date, xcuTemps_val[:, 5], 'Detector Strap_1', Report.color[6])])

            plot4.extend([(xcuTemps_date, xcuTemps_val[:, 3], 'Front Ring', Report.color[13]),
                          (xcuTemps_date, xcuTemps_val[:, 1], 'Mangin', Report.color[17])])
        except:
            pass

        # try:
        #     visthermTemps1_date, visthermTemps1_val = db.getDataBetween("vistherm__lamtemps1",
        #                                                                 "val1_0,val1_1,val1_2,val1_3,val1_4,val1_5,val1_6,val1_7",
        #                                                                 str_date)
        #     visthermTemps1_val = self.checkValues(visthermTemps1_val, ["temp_k"] * 8)
        #     plot2.extend([(visthermTemps1_date, visthermTemps1_val[:, 3], 'Cold_Strap_C_IN,', Report.color[4]),
        #                   (visthermTemps1_date, visthermTemps1_val[:, 2], 'Cold_Strap_C_OUT', Report.color[5]),
        #                   (visthermTemps1_date, visthermTemps1_val[:, 1], 'Field_Lens', Report.color[8]),
        #                   (visthermTemps1_date, visthermTemps1_val[:, 6], 'AIT_Detector Box', Report.color[2]),
        #                   (visthermTemps1_date, visthermTemps1_val[:, 4], 'Thermal_Bar_C_OUT', Report.color[7])])
        #     plot4.append((visthermTemps1_date, visthermTemps1_val[:, 5], 'Spider/Rod Cover C OUT', Report.color[7]))
        # except:
        #     pass
        # try:
        #     visthermTemps2_date, visthermTemps2_val = db.getDataBetween("vistherm__lamtemps2",
        #                                                                 "val1_0,val1_1,val1_2,val1_3,val1_4,val1_5,val1_6,val1_7,val1_8",
        #                                                                 str_date)
        #     visthermTemps2_val = self.checkValues(visthermTemps2_val, ["temp_k"] * 9)
        #
        #     plot2.extend([(visthermTemps2_date, visthermTemps2_val[:, 1], 'LAM_Tip', Report.color[18]),
        #                   (visthermTemps2_date, visthermTemps2_val[:, 6], 'LAM_Spreader', Report.color[1]),
        #                   (visthermTemps2_date, visthermTemps2_val[:, 8], 'Thermal_Bar_C_IN', Report.color[19])])
        #     plot4.extend([(visthermTemps2_date, visthermTemps2_val[:, 7], 'Spider/Rod Cover C IN', Report.color[8]),
        #                   (visthermTemps2_date, visthermTemps2_val[:, 2], 'Detect_Actuator', Report.color[11]),
        #                   (visthermTemps2_date, visthermTemps2_val[:, 3], 'Red_Tube', Report.color[6]),
        #                   (visthermTemps2_date, visthermTemps2_val[:, 4], 'Corrector_Cell', Report.color[0])])
        # except:
        #     pass

        try:
            ccdTemps_date, ccdTemps_val = db.getDataBetween("ccd_r1__ccdtemps", "preamp, ccd0, ccd1", str_date)
            ccdTemps_val = self.checkValues(ccdTemps_val, ["temp_k"] * 3)
            plot2.extend([(ccdTemps_date, ccdTemps_val[:, 1], 'CCD Temps 0', Report.color[4]),
                          (ccdTemps_date, ccdTemps_val[:, 2], 'CCD Temps 1', Report.color[5])])
        except:
            pass

        # try:
        #     aitenv_date, aitenv_val = db.getDataBetween("aitenv__aitenv", "val1_0, val1_1", str_date)
        #     aitenv_val = self.checkValues(aitenv_val, ["temp_c"] * 2)
        #     plot4.extend([(aitenv_date, aitenv_val[:, 0] + 273.15, 'LAM_Env_Rear', Report.color[0]),
        #                   (aitenv_date, aitenv_val[:, 1] + 273.15, 'LAM_Env_Front', Report.color[1])])
        #
        # except:
        #     pass

        try:
            weather_date, weather_val = db.getDataBetween("aitroom__weatherduino", "temp", str_date)
            weather_val = self.checkValues(weather_val, ["temp_c"] * 1)
            plot4.append((weather_date, weather_val[:, 0] + 273.15, 'CleanRoom_Temp', Report.color[15]))
        except:
            pass

        try:
            weather_date2, weather_val2 = db.getDataBetween("aitroom__weatherduino2", "temp", str_date)
            weather_val2 = self.checkValues(weather_val2, ["temp_c"] * 1)
            plot4.append((weather_date2, weather_val2[:, 0] + 273.15, 'CleanRoom_Temp2', Report.color[4]))

        except:
            pass

        try:
            flow_date, flow_val = db.getDataBetween("aitroom__flowduino", "temp", str_date)
            flow_val = self.checkValues(flow_val, ["temp_c"] * 1)
            plot4.append((flow_date, flow_val[:, 0] + 273.15, 'Flow_temp', Report.color[11]))
        except:
            pass

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
            ax1.set_ylabel("Pressure (Torr)", color=Report.color[0])
            for tick in ax1.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(Report.color[0])
                ax1.grid(which='major', alpha=0.5, color=Report.color[0])
                ax1.grid(which='minor', alpha=0.25, color=Report.color[0])
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

            ax2.set_ylabel("Temperature (K)", color=Report.color[18])
            for tick in ax2.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(color=Report.color[18])
                ax3.grid(which='major', alpha=0.0)
                ax2.grid(which='major', alpha=0.5, color=Report.color[18])
                ax2.grid(which='minor', alpha=0.25, color=Report.color[18], linestyle='--')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax2.yaxis.set_minor_locator(minor_locatory)
            ax2.get_yaxis().get_major_formatter().set_useOffset(False)

            ax3.set_ylabel("Power (W)", color=Report.color[10])
            for tick in ax3.yaxis.get_major_ticks():
                tick.label1On = False
                tick.label2On = True
                tick.label2.set_color(color=Report.color[10])
                ax3.grid(which='major', alpha=1.0, color=Report.color[10], linestyle='dashdot')
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

            ax4.set_ylabel("Temperature (K)", color=Report.color[2])
            for tick in ax4.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(color=Report.color[2])
                ax4.grid(which='major', alpha=0.5, color=Report.color[2])
                ax4.grid(which='minor', alpha=0.25, color=Report.color[2], linestyle='--')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax4.yaxis.set_minor_locator(minor_locatory)
            ax4.get_yaxis().get_major_formatter().set_useOffset(False)

            ax5.set_ylabel("Temperature (C)", color=Report.color[10])
            for tick in ax5.yaxis.get_major_ticks():
                tick.label1On = False
                tick.label2On = True
                tick.label2.set_color(color=Report.color[10])
                ax5.grid(which='major', alpha=1.0, color=Report.color[10], linestyle='dashdot')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax5.yaxis.set_minor_locator(minor_locatory)
            ax5.get_yaxis().get_major_formatter().set_useOffset(False)

            box = ax4.get_position()
            ax4.set_position([box.x0, 0.18, box.width, box.height * 0.8])
            ax5.set_position([box.x0, 0.18, box.width, box.height * 0.8])

            lns, labs = self.sortCurve([ax4])
            ax4.legend(lns, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=3, mode="expand", borderaxespad=0.,
                       prop={'size': 9})
            ax5.set_ylim((ax4.get_ylim()[0] - 273.15, ax4.get_ylim()[1] - 273.15))

            ax4.xaxis.set_major_formatter(DateFormatter(self.getDateFormat(ax4.get_xlim())))
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=75, horizontalalignment='right')

        file_name = '/home/pfs/AIT-PFS/jabberLog/PFS_AIT_Report_%s.pdf' % dt.now().strftime("%Y-%m-%d_%H-%M")

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

    def checkValues(self, value, type):
        allMin = {'temp_k': 15, "pressure": 1e-9, "power": 0, "temp_c": -20}
        allMax = {'temp_k': 330, "pressure": 1e4, "power": 250, "temp_c": 50}
        minVal = [allMin[t] for t in type]
        maxVal = [allMax[t] for t in type]
        for i in range(value.shape[1]):
            for j in range(value.shape[0]):
                if not minVal[i] <= value[j][i] < maxVal[i]:
                    value[j][i] = np.nan

        return value

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
