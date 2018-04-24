from collections import OrderedDict
from threading import Thread

import numpy as np
import pandas as pd

from exportdata import exportData, fmtDate, send_file


class Dataset(Thread):
    def __init__(self, pfsbot, user, dstart, dend, step):
        Thread.__init__(self)
        self.pfsbot = pfsbot
        self.user = user

        self.dstart = dstart
        self.dend = dend
        self.step = step

    def run(self):
        fname = self.buildData()
        if fname:
            knownUsers = self.pfsbot.unPickle("knownUsers")
            address = knownUsers[self.user.getNode()]
            send_file(address, fname, '[PFS] AIT Data')
            self.pfsbot.send(self.user, "I've just sent the data to %s" % address)
        else:
            self.pfsbot.send(self.user, "an error has occured")

        return

    def buildData(self, ftime=1.1574073384205501e-5):

        all_data = exportData(pfsbot=self.pfsbot, start=self.dstart, end=self.dend)

        if all_data:
            samp_start = np.max([data.df['tai'].as_matrix()[0] for data in all_data])
            samp_end = np.min([data.df['tai'].as_matrix()[-1] for data in all_data])
            step = self.step * ftime

            ti = np.arange(samp_start, samp_end, step)
            duration = round((ti[-1] - ti[0]) / (ftime * 3600 * 24))

            datas = OrderedDict()
            datas['Time'] = [fmtDate(t) for t in ti]

            for data in all_data:
                for key, label in zip(data.keys, data.tlabel):
                    datas[label] = np.interp(ti, data.df['tai'], data.df[key])

            df = pd.DataFrame.from_dict(datas)
            df = df.set_index('Time')

            fname = '%s/PFS_Data-%s_%s-%iDays.csv' % (self.pfsbot.logFolder,
                                                      self.pfsbot.cam.upper(),
                                                      fmtDate(ti[0], "%Y-%m-%d"),
                                                      duration)

            df.to_csv(fname)

            return fname
