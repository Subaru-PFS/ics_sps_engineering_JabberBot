import os
import pickle
import random
import time

import yaml
from alertsActor.STSpy.radio import Radio


def loadSTSHelp():
    with open(os.path.expandvars('$ICS_ALERTSACTOR_DIR/config/STS.yaml'), 'r') as cfgFile:
        cfg = yaml.load(cfgFile)

    stsHelp = dict()

    for actorCfg in cfg['actors'].values():
        for stsData in sum([data for data in actorCfg.values()], []):
            stsHelp[int(stsData['stsId'])] = stsData['stsHelp']

    return stsHelp


def inAlert(datum):
    value, status = datum.value
    return status != 'OK'


def unPickle(filepath):
    try:
        with open(filepath, 'rb') as thisFile:
            unpickler = pickle.Unpickler(thisFile)
            return unpickler.load()
    except EOFError:
        time.sleep(0.1 + random.random())
        return unPickle(filepath=filepath)


def doPickle(filepath, var):
    with open(filepath, 'wb') as thisFile:
        pickler = pickle.Pickler(thisFile, protocol=2)
        pickler.dump(var)


def loadDatums():
    datums = [Radio.unpack(packet) for packet in unPickle('/software/ait/alarm/packets.pickle')]
    doPickle('/software/ait/alarm/packets.pickle', [])
    return sorted(datums, key=lambda x: x.timestamp)
