import serial
import os, time
import atexit
import logging
import gzip
import subprocess
import shlex
from datetime import datetime, date, timezone
from PigHandler import *

class PigGSM():

    busy = False
    port = False
    curladd = "\"mmsc.mobile.att.net\""
    mmsproxy = "\"172.26.39.1\",80"
    logpath = '/home/pi/PigPen/logs/PigGSM/'
    logger = False

    def setup():
        # Enable Logger
        PigGSM.setupLogger()
        # Enable Serial Communication
        PigGSM.setupSerial()
        # Wait for network
        while True:
            s = PigGSM.checkNetworks().decode('utf-8')
            if s.find('ERROR') != -1:
                time.sleep(60)
            else:
                break
        # Enable auto time updating
        PigGSM.write('AT+CTZU=1')
        PigGSM.logger.info(PigGSM.waitForInput())

    def setupLogger():
        if not os.path.isdir(PigGSM.logpath):
            if not os.path.isdir('/home/pi/PigPen/logs'):
                os.mkdir('/home/pi/PigPen/logs')
            os.mkdir(PigGSM.logpath)
        if not PigGSM.logger:
            logname = 'PigGSM'
            PigGSM.logger = logging.getLogger(logname)
            handle = PigHandler(os.path.join(PigGSM.logpath, logname), when='midnight')
            form = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handle.setFormatter(form)
            PigGSM.logger.addHandler(handle)
            PigGSM.logger.setLevel(logging.INFO)

    def setupSerial():
        if not PigGSM.port:
            # might be /dev/ttys0
            PigGSM.port = serial.Serial("/dev/ttyAMA0", baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=1)
            while True:
                PigGSM.write('AT')
                recv = PigGSM.waitForInput(5)
                if(recv == 'AT\r\r\nOK\r\n'.encode('utf-8')):
                    PigGSM.logger.info(recv)
                    PigGSM.write('AT+CMMSEDIT=0')
                    PigGSM.logger.info(PigGSM.waitForInput())
                    break

    def sendImage(rec, path):
        PigGSM.sendPigMMS(rec, PigMMS(PigMMSData('PIC', path)))

    def sendPigMMS(rec, mms):
        busy = True
        PigGSM.write("AT+CMGF=1")
        PigGSM.logger.info(PigGSM.waitForInput())
        PigGSM.write("AT+CMMSCURL=" + PigGSM.curladd)
        PigGSM.logger.info(PigGSM.waitForInput())
        PigGSM.write("AT+CMMSPROTO=1," + PigGSM.mmsproxy)
        PigGSM.logger.info(PigGSM.waitForInput())
        PigGSM.write("AT+CGSOCKCONT=1,\"IP\",\"phone\"")
        PigGSM.logger.info(PigGSM.waitForInput())
        PigGSM.write("AT+CMMSEDIT=1")
        PigGSM.logger.info(PigGSM.waitForInput())
        for data in mms.data:
            PigGSM.port.write(data.getCommand())
            PigGSM.logger.info(PigGSM.waitForInput())
            PigGSM.port.write(data.getData())
            time.sleep(1)
            PigGSM.port.flushInput()
        PigGSM.write("AT+CMMSRECP=\"" + rec + "\"")
        PigGSM.logger.info(PigGSM.waitForInput())
        PigGSM.write("AT+CMMSSEND")
        while True:
            recv = PigGSM.waitForInput()
            PigGSM.logger.info(recv)
            recv = recv.decode('utf-8')
            if(recv.find('ERROR') != -1):
                PigGSM.refreshNet()
                break
            if(recv.find('+CMMSSEND:') != -1):
                if(recv.find('+CMMSSEND: 0') != -1):
                    break
                else:
                    PigGSM.refreshNet()
                    PigGSM.write("AT+CMMSSEND")
                    
                
        
        PigGSM.write("AT+CMMSEDIT=0")
        PigGSM.logger.info(PigGSM.waitForInput())
        PigGSM.busy = False

    def sendText(rec, text):
        PigGSM.sendPigMMS(rec, PigMMS(PigMMSData('TEXT', text)))

    def listSMS():
        PigGSM.busy = True
        PigGSM.write('AT+CMGL=\"ALL\"')
        SMSstr = PigGSM.waitForInput()
        SMSstr = SMSstr.decode('utf-8')
        PigGSM.busy = False
        i = SMSstr.find('\r\nOK\r\n')
        if i == -1:
            return False
        else:
            SMSstr = SMSstr[:i]
        SMSs = SMSstr.split('+CMGL: ')
        del SMSs[0]
        SMS = []
        for mess in SMSs:
            SMS.append(PigRecSMS(mess))
        return SMS

    def getSMS(index):
        PigGSM.busy = True
        PigGSM.write('AT+CMGR=' + str(int(index)))
        SMSstr = PigGSM.waitForInput()
        PigGSM.logger.info(SMSstr)
        string = SMSstr.decode('utf-8')
        PigGSM.busy = False
        oki = string.find('\r\nOK\r\n')
        if(oki != -1):
            string = string[:oki]
            string = string.replace('AT+CMGR=' + str(int(index)) + '\r\r\n+CMGR: ', '')
            string = str(int(index)) + "," + string
            return PigRecSMS(string)
        else:
            return False

    def printSMS(SMS):
        stringy = 'Index: ' + str(int(SMS.index)) + '\n'
        stringy += 'From: ' + str(SMS.number) + '\n'
        stringy += 'Date: ' + str(SMS.date) + '\n'
        stringy += 'State: ' + str(SMS.stat) + '\n'
        stringy += '--- TEXT ---\n'
        stringy += str(SMS.message)
        return stringy

    def deleteSMS(index, delflag = 0):
        if(isinstance(index, PigRecSMS)):
            index = index.index
        PigGSM.busy = True
        PigGSM.write('AT+CMGD=' + str(index) + ',' + str(delflag))
        SMSstr = PigGSM.waitForInput()
        PigGSM.logger.info(SMSstr)
        string = SMSstr.decode('utf-8')
        PigGSM.busy = False
        oki = string.find('\r\nOK\r\n')
        if(oki != -1):
            return True
        else:
            return False

    def checkNetReg():
        PigGSM.write('AT+CREG?')
        s = PigGSM.waitForInput()
        PigGSM.logger.info(s)
        return s

    def enableNetReg():
        PigGSM.write('AT+CREG=1')
        s = PigGSM.waitForInput()
        PigGSM.logger.info(s)
        return s

    def checkNetworks():
        PigGSM.write('AT+COPS=?')
        PigGSM.logger.info(PigGSM.waitForInput())
        s = PigGSM.waitForInput()
        PigGSM.logger.info(s)
        return s
        
    def refreshNet():
        s = PigGSM.checkNetReg().decode('utf-8')
        if s.find(',1') == -1:
            PigGSM.enableNetReg()
            PigGSM.checkNetworks()

    def getTime():
        PigGSM.write('AT+CCLK?')
        s = PigGSM.waitForInput()
        PigGSM.logger.info(s)
        s = s.decode('utf-8')
        s = s.split('CCLK: ')[1]
        s = s[:s.find('\r\nOK\r\n')]
        s = s.replace('"', '')
        if(s.find('+') != -1):
            s, tz = s.split('+')
        else:
            s, tz = s.split('-')
        tz = int(tz)
        dt  = datetime.strptime(s, '%y/%m/%d,%H:%M:%S')
        return dt
    
    def write(command):
        # Transmitting AT Commands to the Modem
        # '\r' indicates the Enter key
        command += '\r'
        byter = command.encode('utf-8')
        PigGSM.port.write(byter)

    def read(length = 10):
        rcv = PigGSM.port.read(length)
        return rcv.decode("utf-8")

    def readAll():
        rcv = bytes()
        while PigGSM.port.inWaiting():
            rcv += PigGSM.port.read()
        #return rcv.decode("utf-8")
        return rcv

    def waitForInput(timeout = 60):
        stamp = datetime.fromtimestamp(time.time())
        while PigGSM.port.inWaiting() == 0:
            time.sleep(0.1)
            delta = datetime.fromtimestamp(time.time()) - stamp
            if delta.seconds > timeout:
                break
        return PigGSM.readAll()

    def waitWhileBusy():
        while(PigGSM.busy):
            time.sleep(0.1)

PigGSM.setup()

# Object used for sending MMS via PigGSM.sendPigMMS(PigMMS)
class PigMMS(object):

    data = []
    def __init__(self, datar = []):
        self.setData(datar)

    def setData(self, datar = []):
        if(isinstance(datar, PigMMSData)):
            self.data = []
            self.data.append(datar)
            return True
        elif(datar == []):
            self.data = []
            return True
        elif(hasattr(datar, '__len__') and all(isinstance(x, PigMMSData) for x in datar)):
            self.data = datar
            return True
        else:
            return False
            
    def addData(self, datar):
        if(isinstance(datar, PigMMSData)):
            self.data.append(datar)
            return True
        elif(hasattr(datar, '__len__') and all(isinstance(x, PigMMSData) for x in datar)):
            self.data.extend(datar)
            return True
        else:
            return False

# Object used by PigMMS to store data to be sent via 'AT+CMMSDOWN'
class PigMMSData(object):
    
    dataType = ''
    data = ''
    def __init__(self, dType = 'TEXT', d = 'you forgot to set the data dummy'):
        self.setData(dType, d)
        
    def setData(self, dType = 'TEXT', d = 'you forgot to set the data dummy'):
        self.dataType = dType
        self.data = d

    ### NEED TO CLEAN THIS UP TO BETTER MATCH THE DATA TYPES ###
    def getCommand(self):
        if((self.dataType == 'PIC')):
            if(os.path.isfile(self.data)):
                title = self.data.split(os.path.sep)[-1]
            else:
                title = 'file.jpg'
            return str("AT+CMMSDOWN=\"" + self.dataType + "\"," + str(len(self.getData())) + ",\"" + title + "\"\r").encode('utf-8')
        elif(self.dataType == 'TEXT'):
            return str("AT+CMMSDOWN=\"" + self.dataType + "\"," + str(len(self.getData())) + ",\"Text.txt\"\r").encode('utf-8')
        elif(self.dataType == 'TITLE'):
            return str("AT+CMMSDOWN=\"" + self.dataType + "\"," + str(len(self.getData())) + "\r").encode('utf-8')
        else:
            return False

    def getData(self):
        if(self.dataType == 'PIC' or self.dataType == 'FILE') and os.path.isfile(self.data):
            return open(self.data,"rb").read()
        elif(isinstance(self.data, str)):
            return self.data.encode('utf-8')
        else:
            return self.data

# Object used to store and format recieved SMS messages
class PigRecSMS(object):
    
    def __init__(self, stringy = ''):
        self.parseString(stringy)

    def parseString(self, stringy):
        while(stringy[-2:] == '\r\n'):
            stringy = stringy[:-2]
        stringy = stringy.replace('\"', "")
        arr, self.message = stringy.split('\r\n', 1)
        arr = arr.split(',')
        self.index = int(arr[0])
        self.stat = arr[1]
        self.number = arr[2].replace('+', "")
        self.date = arr[4] + "," + arr[5]
