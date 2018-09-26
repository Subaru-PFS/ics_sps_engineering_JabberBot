import pickle
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename

from Crypto.Cipher import AES
from matplotlib.dates import num2date
from sps_engineering_Lib_dataQuery.confighandler import loadConf
from sps_engineering_Lib_dataQuery.databasemanager import DatabaseManager


def getConf(fullConfig, tablename, method='both'):
    for conf in fullConfig:
        if conf.tablename == tablename:
            if method == 'both':
                conf.tlabel = ['%s-%s' % (conf.deviceLabel, label) for label in conf.labels]
            elif method == 'devname':
                conf.tlabel = [conf.deviceLabel]
            elif method == 'probname':
                conf.tlabel = conf.labels

            return conf

    return False


def exportData(pfsbot, start, end=False):

    db = DatabaseManager(pfsbot.db_addr, pfsbot.db_port)
    db.init()

    fullConfig = loadConf(date=start)
    # optional = {'b1': [getConf(fullConfig=fullConfig, tablename='aitroom__roughpressure', method='devname')],
    #             'r1': []}
    optional = {'b1': [],
                'r1': []}
    devices = []

    ionGauge = getConf(fullConfig=fullConfig, tablename='xcu_%s__pressure' % pfsbot.cam, method='devname')
    if ionGauge:
        devices.append(ionGauge)

    ionPump1 = getConf(fullConfig=fullConfig, tablename='xcu_%s__ionpump1' % pfsbot.cam, )
    if ionPump1:
        devices.append(ionPump1)

    ionPump2 = getConf(fullConfig=fullConfig, tablename='xcu_%s__ionpump2' % pfsbot.cam, )
    if ionPump2:
        devices.append(ionPump2)

    cooler = getConf(fullConfig=fullConfig, tablename='xcu_%s__coolertemps' % pfsbot.cam)
    if cooler:
        devices.append(cooler)

    temps = getConf(fullConfig=fullConfig, tablename='xcu_%s__temps' % pfsbot.cam, method='probname')
    if temps:
        devices.append(temps)

    ccdtemps = getConf(fullConfig=fullConfig, tablename='ccd_%s__ccdtemps' % pfsbot.cam, method='probname')
    if ccdtemps:
        devices.append(ccdtemps)

    turbospeed = getConf(fullConfig=fullConfig, tablename='xcu_%s__turbospeed' % pfsbot.cam)
    if turbospeed:
        devices.append(turbospeed)

    gatevalve = getConf(fullConfig=fullConfig, tablename='xcu_%s__gatevalve' % pfsbot.cam)
    if gatevalve:
        devices.append(gatevalve)

    weather = getConf(fullConfig=fullConfig, tablename='aitroom__weatherduino')
    if weather:
        devices.append(weather)

    weather2 = getConf(fullConfig=fullConfig, tablename='aitroom__weatherduino2')
    if weather2:
        devices.append(weather2)

    for opt in optional[pfsbot.cam]:
        if opt:
            devices.append(opt)

    for device in devices:
        try:
            device.df = db.dataBetween(table=device.tablename,
                                       cols=','.join(device.keys),
                                       start=start,
                                       end=end)
        except ValueError:
            device.df = None

    return [device for device in devices if device.df is not None]


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
