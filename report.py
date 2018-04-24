import matplotlib as mpl

mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_pdf import PdfPages

from threading import Thread
from exportdata import exportData, send_file, fmtDate
from datetime import datetime as dt

colors = ['#1f78c5', '#ff801e', '#2ca13c', '#d82738', '#9568cf', '#8d565b', '#e578c3', '#17bfd1', '#808080',
          '#caca76', '#000000', '#acc5f5', '#fcb986', '#96dc98', '#fc96a4', '#c3aee2', '#c29aa2', '#f4b4cf',
          '#9cd7e2', '#fdff43', '#c5c5c5']


class Data(object):
    def __init__(self, dates, values, label):
        object.__init__(self)
        self.dates = dates
        self.values = values
        self.label = label


class Report(Thread):
    def __init__(self, pfsbot, timedelta, user):

        Thread.__init__(self)

        t0 = dt.utcnow()
        datestart = (t0 - timedelta).isoformat()

        self.datestart = datestart
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

    def generate_pdf(self, ftime=1.1574073384205501e-5):
        fig1 = None
        fig2 = None
        fig3 = None

        all_data = exportData(pfsbot=self.pfsbot, start=self.datestart)
        pressure_plot = []
        power_plot = []
        coldtemp_plot = []
        warmtemp_plot = []

        unRelevant = []

        for data in all_data:
            for key, label, typ in zip(data.keys, data.tlabel, data.types):
                if label in unRelevant:
                    continue
                offset = 273.15 if typ == 'temperature_c' else 0
                values = data.df[key] + offset
                newdata = Data(dates=data.df['tai'], values=values, label=label)

                if typ == 'pressure_torr':
                    pressure_plot.append(newdata)

                elif typ == 'power':
                    power_plot.append(newdata)

                elif typ in ['temperature_c', 'temperature_k']:
                    if np.mean(values) > 270:
                        warmtemp_plot.append(newdata)
                    else:
                        coldtemp_plot.append(newdata)
                else:
                    pass

        if pressure_plot:
            fig1 = plt.figure()
            ax1 = fig1.add_subplot(111)

            for i1, data in enumerate(pressure_plot):
                ax1.plot_date(data.dates, data.values, '-', label=data.label, color=colors[i1])

            axecol = colors[0]

            ax1.set_yscale('log', basey=10)
            colorStyle(ax=ax1, ylabel="Pressure (Torr)", color=axecol, primAxis=True)

            box = ax1.get_position()
            ax1.set_position([box.x0, 0.18, box.width, box.height * 0.8])
            lns, labs = sortCurve([ax1])
            ax1.legend(lns, labs, bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=3, mode="expand", borderaxespad=0.,
                       prop={'size': 8})
            ax1.xaxis.set_major_formatter(DateFormatter(getDateFormat(ax1.get_xlim())))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=20, horizontalalignment='center')
            fig1.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1, hspace=0.01)

        if coldtemp_plot:
            fig2 = plt.figure()
            ax2 = fig2.add_subplot(111)

            for i2, data in enumerate(coldtemp_plot):
                ax2.plot_date(data.dates, data.values, '-', label=data.label, color=colors[i2])

            axe2col = colors[0]
            colorStyle(ax=ax2, ylabel="Temperature (K)", color=axe2col, primAxis=True)

            box = ax2.get_position()
            ax2.set_position([box.x0, 0.18, box.width, box.height * 0.8])

            if power_plot:
                ax3 = ax2.twinx()
                axe3col = colors[i2 + 1]

                for i3, data in enumerate(power_plot):
                    ax3.plot_date(data.dates, data.values, '-', label=data.label, color=colors[i2 + 1 + i3])

                colorStyle(ax=ax3, ylabel="Power (W)", color=axe3col, primAxis=False)
                ax3.set_position([box.x0, 0.18, box.width, box.height * 0.8])
                lns, labs = sortCurve([ax2, ax3])

            else:
                lns, labs = sortCurve([ax2])

            ax2.legend(lns, labs,
                       bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=4,
                       mode="expand", borderaxespad=0., prop={'size': 5.4})
            ax2.xaxis.set_major_formatter(DateFormatter(getDateFormat(ax2.get_xlim())))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=20, horizontalalignment='center')

            fig2.subplots_adjust(left=0.1, right=0.89, top=0.80, bottom=0.1, hspace=0.01)

        if warmtemp_plot:

            fig3 = plt.figure()
            ax4 = fig3.add_subplot(111)
            ax5 = ax4.twinx()

            for i4, data in enumerate(warmtemp_plot):
                ax4.plot_date(data.dates, data.values, '-', label=data.label, color=colors[i4])

            axe4col = colors[0]
            axe5col = colors[i4 + 1]

            colorStyle(ax=ax4, ylabel="Temperature (K)", color=axe4col, primAxis=True)
            colorStyle(ax=ax5, ylabel="Temperature (C)", color=axe5col, primAxis=False)

            box = ax4.get_position()
            ax4.set_position([box.x0, 0.18, box.width, box.height * 0.8])
            ax5.set_position([box.x0, 0.18, box.width, box.height * 0.8])

            lns, labs = sortCurve([ax4])
            ax4.legend(lns, labs,
                       bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=4,
                       mode="expand", borderaxespad=0., prop={'size': 5.4})

            ax5.set_ylim((ax4.get_ylim()[0] - 273.15, ax4.get_ylim()[1] - 273.15))

            ax4.xaxis.set_major_formatter(DateFormatter(getDateFormat(ax4.get_xlim())))
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=20, horizontalalignment='center')

            fig3.subplots_adjust(left=0.1, right=0.89, top=0.80, bottom=0.1, hspace=0.01)

            all_plots = pressure_plot + coldtemp_plot + warmtemp_plot + power_plot
            samp_start = max([data.dates.as_matrix()[0] for data in all_plots])
            samp_end = min([data.dates.as_matrix()[-1] for data in all_plots])

            duration = round((samp_end - samp_start) / (ftime * 3600 * 24))

            file_name = '%s/PFS_AIT_Report-%s_%s-%iDays.pdf' % (self.pfsbot.logFolder,
                                                                self.pfsbot.cam.upper(),
                                                                fmtDate(samp_start, "%Y-%m-%d"),
                                                                duration)

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


def getDateFormat(dates):
    t0, tmax = dates

    if tmax - t0 > 7:
        format_date = "%Y-%m-%d"
    elif tmax - t0 > 1:
        format_date = "%a %H:%M"
    else:
        format_date = "%H:%M:%S"
    return format_date


def sortCurve(list_axes):
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


def colorStyle(ax, ylabel, color, primAxis, fontsize=8):
    ax.set_ylabel(ylabel, color=color, fontsize=fontsize)
    setTickLocator(ax)

    for tick in (ax.yaxis.get_major_ticks() + ax.yaxis.get_minor_ticks()):
        pimpTicks(tick, primAxis, color)

    [maj_style, min_style, alpha2] = ['--', '-', 0.15] if primAxis else [':', '-.', 0.1]

    ax.grid(which='major', alpha=0.6, color=color, linestyle=maj_style)
    ax.grid(which='minor', alpha=alpha2, color=color, linestyle=min_style)

    ax.tick_params(axis='y', labelsize=fontsize)


def setTickLocator(ax):
    if ax.get_yscale() in ['log']:
        ax.yaxis.set_minor_locator(ticker.LogLocator(subs=[2, 3, 6]))
        # ax.yaxis.set_minor_formatter(ticker.FormatStrFormatter('%.1e'))

    else:
        minor_locatory = ticker.AutoMinorLocator(5)
        ax.yaxis.set_minor_locator(minor_locatory)
        ax.get_yaxis().get_major_formatter().set_useOffset(False)

    minor_locatorx = ticker.AutoMinorLocator(5)
    ax.xaxis.set_minor_locator(minor_locatorx)


def pimpTicks(tick, primAxis, color):
    tick.label1On = True if primAxis else False
    tick.label2On = False if primAxis else True

    coloredTick = tick.label1 if primAxis else tick.label2
    coloredTick.set_color(color=color)
