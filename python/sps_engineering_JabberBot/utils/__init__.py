import os
import pickle
import random
import time

import yaml
from STSpy.radio import Radio


class AlertBuffer(list):
    samplingTime = 300

    def __init__(self):
        list.__init__(self)
        self.sent = dict()

    @property
    def current(self):
        return dict([(k, v) for k, v in self.sent.items() if (time.time() - v.sendTime) <= AlertBuffer.samplingTime])

    def filterTraffic(self):
        return [datum for datum in self.__iter__() if self.doSend(datum)]

    def check(self, datum):
        try:
            prev = self.sent[datum.id]
        except KeyError:
            return True

        if (time.time() - prev.sendTime) > AlertBuffer.samplingTime:
            return True

        prevValue, prevState = prev.value
        currValue, currState = datum.value

        if (currState != 'OK' and prevState == 'OK') or (currState == 'OK' and prevState != 'OK'):
            return True

        return False

    def doSend(self, datum):
        doSend = self.check(datum)
        if doSend:
            datum.sendTime = time.time()
            self.sent[datum.id] = datum

        return doSend

    def clear(self):
        del self[:]


def loadSTSHelp():
    """"""
    # Cannot pfs_insdata func, because we're using /usr/bin/python and pfs_instdata is python3 no (__init__.py) meh...
    with open(os.path.expandvars('$PFS_INSTDATA_DIR/config/alerts/STS.yaml'), 'r') as cfgFile:
        stsCfg = yaml.load(cfgFile)['actors']

    with open(os.path.expandvars('$PFS_INSTDATA_DIR/config/alerts/AIT@LAM.yaml'), 'r') as cfgFile:
        lamCfg = yaml.load(cfgFile)['actors']

    stsCfg.update(lamCfg)

    stsHelp = dict()

    for actorCfg in stsCfg.values():
        for stsData in sum([data for data in actorCfg.values()], []):
            stsHelp[int(stsData['stsId'])] = stsData['stsHelp']

    return stsHelp


def inAlert(datum):
    value, status = datum.value
    return status != 'OK'


def getUserAlert():
    return unPickle('userAlert')


def setUserAlert(userAlert):
    return doPickle('userAlert', userAlert)


def readState():
    return unPickle('state')


def writeState(state):
    return doPickle('state', state)


def unPickle(filename, folder='/software/ait/alerts', retType=dict):
    filepath = os.path.join(folder, '%s.pickle' % filename)

    try:
        with open(filepath, 'rb') as thisFile:
            unpickler = pickle.Unpickler(thisFile)
            return unpickler.load()
    except EOFError:
        time.sleep(0.1 + random.random())
        return unPickle(filename, folder)
    except IOError:
        return retType()


def doPickle(filename, var, folder='/software/ait/alerts'):
    filepath = os.path.join(folder, '%s.pickle' % filename)

    with open(filepath, 'wb') as thisFile:
        pickler = pickle.Pickler(thisFile, protocol=2)
        pickler.dump(var)


def loadDatums():
    packets = unPickle('packets', retType=list)
    datums = [Radio.unpack(packet) for packet in packets]
    doPickle('packets', [])
    return sorted(datums, key=lambda x: x.timestamp)
