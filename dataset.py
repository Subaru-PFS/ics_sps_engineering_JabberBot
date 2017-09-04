import ConfigParser
import os
from datetime import datetime as dt
from threading import Thread

import numpy as np
import pandas as pd

from exportdata import exportData, fmtDate, send_file


class Dataset(Thread):
    def __init__(self, pfsbot, user, dstart, dend, step):
        Thread.__init__(self)
        self.pfsbot = pfsbot
        self.user = user
        self.curveDict = {}

        self.dstart = dstart
        self.dend = dend
        self.step = step

    def run(self):
        self.readCfg(self.pfsbot.config_path)
        fname = self.buildData()
        if fname:
            address = self.pfsbot.knownUsers[self.user.getNode()]
            send_file(address, fname, '[PFS] AIT Data')
            self.pfsbot.send(self.user, "I've just sent the data to %s" % address)
        else:
            self.pfsbot.send(self.user, "an error has occured")

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

    def buildData(self, ftime=1.1574073384205501e-5):

        dates = [self.dstart.strftime("%d/%m/%Y %H:%M:%S"), self.dend.strftime("%d/%m/%Y %H:%M:%S")]

        plot1, plot2, plot3, plot4 = exportData(pfsbot=self.pfsbot, dates=dates, rm=[])
        plots = plot1 + plot2 + plot3 + plot4
        if plots:
            samp_start = np.max([data.tstamp[0] for data in plots])
            samp_end = np.min([data.tstamp[-1] for data in plots])
            step = self.step * ftime

            ti = np.arange(samp_start, samp_end, step)
            duration = round((ti[-1] - ti[0]) / (ftime*3600*24))

            datas = {'Time': [fmtDate(t) for t in ti]}

            for data in plots:
                datas[data.label] = np.interp(ti, data.tstamp, data.vals)

            df = pd.DataFrame.from_dict(datas)
            df = df.set_index('Time')

            fname = '%s/PFS_Data-%s_%s-%iDays.csv' % (self.pfsbot.logFolder,
                                                      self.pfsbot.cam.upper(),
                                                      fmtDate(ti[0], "%Y-%m-%d"),
                                                      duration)

            df.to_csv(fname)

            return fname
