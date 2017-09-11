import matplotlib as mpl

mpl.use('Agg')
import matplotlib.pyplot as plt

from matplotlib import ticker
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages

from threading import Thread
from exportdata import exportData, send_file
from datetime import datetime as dt


class Report(Thread):
    def __init__(self, pfsbot, timedelta, user):

        Thread.__init__(self)

        t0 = dt.now()
        str_date = (t0 - timedelta).strftime("%d/%m/%Y %H:%M:%S")

        self.str_date = str_date
        self.pfsbot = pfsbot
        self.user = user

    def run(self):
        file_name = self.generate_pdf()
        if file_name:
            knownUsers = self.pfsbot.unPickle("knownUsers")
            address = knownUsers[self.user.getNode()]
            send_file(address, file_name, '[PFS] AIT Report')
            self.pfsbot.send(self.user, "I've just sent the report to %s" % address)
        else:
            self.pfsbot.send(self.user, "an error has occured")
        return

    def generate_pdf(self):
        fig1 = None
        fig2 = None
        fig3 = None

        plot1, plot2, plot3, plot4 = exportData(pfsbot=self.pfsbot, dates=[self.str_date], rm=["Field Lens",
                                                                                               'Red Tube2'])
        if plot1:
            fig1 = plt.figure()
            ax1 = fig1.add_subplot(111)

            for data in plot1:
                date, values, label, col = data.props
                ax1.plot_date(date, values, '-', label=label, color=col)

            axecol = plot1[0].col

            ax1.set_yscale('log', basey=10)
            subs = [1.0, 2.0, 3.0, 5.0]  # ticks to show per decade
            ax1.yaxis.set_minor_locator(ticker.LogLocator(subs=subs))  # set the ticks position
            minor_locatorx = ticker.AutoMinorLocator(5)
            ax1.xaxis.set_minor_locator(minor_locatorx)
            ax1.set_ylabel("Pressure (Torr)", color=axecol)
            for tick in ax1.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(axecol)
                ax1.grid(which='major', alpha=0.5, color=axecol)
                ax1.grid(which='minor', alpha=0.25, color=axecol)
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

            for data in plot2:
                date, values, label, col = data.props
                ax2.plot_date(date, values, '-', label=label, color=col)

            axe2col = plot2[0].col
            axe3col = plot3[0].col if plot3 else axe2col
            if plot3:
                for data in plot3:
                    date, values, label, col = data.props
                    ax3.plot_date(date, values, '-', label=label, color=col)

            ax2.set_ylabel("Temperature (K)", color=axe2col)
            for tick in ax2.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(color=axe2col)
                ax3.grid(which='major', alpha=0.0)
                ax2.grid(which='major', alpha=0.5, color=axe2col)
                ax2.grid(which='minor', alpha=0.25, color=axe2col, linestyle='--')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax2.yaxis.set_minor_locator(minor_locatory)
            ax2.get_yaxis().get_major_formatter().set_useOffset(False)

            ax3.set_ylabel("Power (W)", color=axe3col)
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

            for data in plot4:
                date, values, label, col = data.props
                ax4.plot_date(date, values, '-', label=label, color=col)

            axe4col = plot4[0].col
            axe5col = plot3[0].col

            ax4.set_ylabel("Temperature (K)", color=axe4col)
            for tick in ax4.yaxis.get_major_ticks():
                tick.label1On = True
                tick.label2On = False
                tick.label1.set_color(color=axe4col)
                ax4.grid(which='major', alpha=0.5, color=axe4col)
                ax4.grid(which='minor', alpha=0.25, color=axe4col, linestyle='--')
            minor_locatory = ticker.AutoMinorLocator(5)
            ax4.yaxis.set_minor_locator(minor_locatory)
            ax4.get_yaxis().get_major_formatter().set_useOffset(False)

            ax5.set_ylabel("Temperature (C)", color=axe5col)
            for tick in ax5.yaxis.get_major_ticks():
                tick.label1On = False
                tick.label2On = True
                tick.label2.set_color(color=axe5col)
                ax5.grid(which='major', alpha=1.0, color=axe5col, linestyle='dashdot')
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

        file_name = '%s/PFS_AIT_Report-%s_%s.pdf' % (self.pfsbot.logFolder,
                                                     self.pfsbot.cam.upper(),
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
