import RPi.GPIO as GPIO
import time
from datetime import datetime, date
import logging
import sys
import yaml

from PigGate import *
from PigCamera import *
from PigGSM import *

class PigPen():

        OWNER = False
        pcamera = False
        pgate = False
        pmotion = False
        pmtimestamp = 0
        logpath = '/home/pi/PigPen/logs/'
        logger = False
        config = False

        def main():
                PigPen.setup()
                try:
                        while True:
                                if PigPen.pmotion:
                                        mms = PigPen.grabMMSfromCamera(PigPen.pcamera)
                                        for number in PigPen.OWNER:
                                                PigGSM.sendPigMMS(number, mms)
                                        PigPen.pmotion = False
                                PigPen.parseSMSforCommands()
                                time.sleep(1)
                except:
                        PigPen.logger.exception('PigPen encountered an error and had to close')
                        GPIO.cleanup()           # clean up GPIO on normal exit  

        def setup():
                PigPen.setupLogger()
                PigPen.logger.info('Initiating PigPen...')
                PigPen.loadConfig()
                PigPen.setupTime()
                PigPen.setupCamera()
                PigPen.setupGate()
                PigPen.setupMotion()
                PigPen.logger.info('PigPen Initiated')

        def setupCamera():
                PigPen.pcamera = PigCamera(PigPen.config['camera']['relayNumber'], PigPen.config['camera']['relayAddress'], PigPen.config['camera']['cameraIP'], PigPen.config['camera']['user'], PigPen.config['camera']['password'], PigPen.config['camera']['port'], PigPen.config['camera']['channel'], PigPen.config['camera']['subtype'], PigPen.config['camera']['maxBytes'])

        def setupGate():
                PigPen.pgate = PigGate(PigPen.config['gate']['relayNumber'], PigPen.config['gate']['relayAddress'], PigPen.config['gate']['detectionPin'])

        def setupMotion():
                PigPen.pmotion = False
                PigPen.pmtimestamp = time.time()
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(PigPen.config['motion']['pin'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(PigPen.config['motion']['pin'], GPIO.FALLING, callback=PigPen.rising, bouncetime=300)
                PigPen.logger.info('Motion Detector set to pin ' + str(PigPen.config['motion']['pin']))
        
        def setupLogger():
                if not os.path.isdir(PigPen.logpath):
                        os.mkdir(PigPen.logpath)
                if not PigPen.logger:
                        logname = 'PigPen'
                        PigPen.logger = logging.getLogger(logname)
                        handle = PigHandler(os.path.join(PigPen.logpath, logname), when='midnight')
                        handlecon = logging.StreamHandler()
                        form = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
                        handle.setFormatter(form)
                        handlecon.setFormatter(form)
                        PigPen.logger.addHandler(handle)
                        PigPen.logger.addHandler(handlecon)
                        PigPen.logger.setLevel(logging.INFO)
						
        def setupTime():
                PigPen.logger.info('Setting current time...')
                dt = PigGSM.getTime()
                s = '\'' + dt.strftime('%Y-%m-%d %H:%M:%S') + '\''
                subprocess.call(shlex.split("sudo date -s " + s))
                PigPen.logger.info('Current time set to ' + s)

        def loadConfig():
                PigPen.logger.info('Loading config...')
                file = open('/home/pi/PigPen/config.yml')
                PigPen.config = yaml.safe_load(file)
                file.close()
                PigPen.OWNER = PigPen.config['owner']
                PigPen.logger.info('Config loaded')
                
        
        def rising(channel):
                PigPen.logger.info('Motion detected')
                if PigPen.pgate.isOpen():
                        delta = PigPen.timeSinceLast()
                        if delta.days > 0 or delta.seconds >= PigPen.config['motion']['delay']:
                                PigPen.logger.info(str(delta.total_seconds()) + 's since last event, triggering motion based picture')
                                PigPen.pmtimestamp = time.time()
                                PigPen.pmotion = True
                        else:
                                PigPen.logger.info('Only ' + str(delta.total_seconds()) + 's since last event, motion is discarded')
                else:
                        PigPen.logger.info('Gate is closed so motion is discarded')
                
        def timeSinceLast():
                last = datetime.fromtimestamp(PigPen.pmtimestamp)
                now = datetime.fromtimestamp(time.time())
                return now - last

        def grabAndSendImage(camera, rec):
                PigPen.logger.info('Sending image from ' + camera.toString() + ' to ' + rec)
                PigGSM.sendPigMMS(rec, PigPen.grabMMSfromCamera(camera))
                PigPen.logger.info('Message Sent')

        def grabMMSfromCamera(camera):
                PigPen.pmtimestamp = time.time()
                file = camera.grabImage()
                date = file.split(os.path.sep)[-1].replace('.jpg', '')
                mms = PigMMS([PigMMSData('TITLE', date), PigMMSData('PIC', file)])
                return mms
                

        def closeGate(gate):
                if(gate.isOpen()):
                        gate.switch()
                        return True
                else:
                        return False

        def sendHelp(rec):
                PigPen.logger.info('Sending help message to ' + rec)
                halp = 'Reply with \'c\' to close the gate or \'v\' to view the pen camera.'
                PigGSM.sendText(rec, halp)

        def parseSMSforCommands():
                SMSs = PigGSM.listSMS()
                if(hasattr(SMSs, '__iter__')):
                        for SMS in SMSs:
                                PigPen.logger.info('New Message:' + '\n' + PigGSM.printSMS(SMS))
                                if SMS.number in PigPen.OWNER:
                                        PigPen.logger.info('They are an Owner, parsing for commmand...')
                                        PigPen.commandMap(SMS.message, SMS.number)
                                else:
                                        PigPen.logger.info('They are not an Owner')
                                PigPen.logger.info('Deleting Message')
                                PigGSM.deleteSMS(SMS.index)
                
        def commandMap(command, number):
                command = str(command).lower()
                command = command.strip()
                if(command == 'c' or command == 'close'):
                        if PigPen.closeGate(PigPen.pgate):
                                PigPen.logger.info(number + ' has closed the gate')
                                PigGSM.sendText(number, 'The gate has been closed')
                        else:
                                PigPen.logger.info(number + ' tried closing the gate, but it is already closed')
                                PigGSM.sendText(number, 'The gate is already closed')
                elif(command == 'v' or command == 'view'):
                        PigPen.logger.info(number + ' requested an image')
                        PigPen.grabAndSendImage(PigPen.pcamera, number)
                else:
                        PigPen.logger.info('Could not parse command from ' + number)
                        PigPen.sendHelp(number)
                














if  __name__ =='__main__':
    PigPen.main()
