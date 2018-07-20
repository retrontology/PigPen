import time
import pifacerelayplus
import RPi.GPIO as GPIO
import logging

class PigGate():
        
        # Constructor, grab relay board address and relay number on addressed board
        def __init__(self, num, add, pin):
                self.setRelay(num, add)
                self.setDetect(pin)
                self.setupLogger()
                self.log('Initiated')
                
        def setupLogger(self):
                self.logger = logging.getLogger('PigPen')

        def log(self, stringy):
                self.logger.info('[' + self.toString() + '] ' + stringy)

        def setRelayAddress(self, add):
                self.relayAddress = add
                self.pfr = pifacerelayplus.PiFaceRelayPlus(pifacerelayplus.RELAY, self.relayAddress)
                
        def setRelayNumber(self, num):
                self.relayNumber = num
                
        def setRelay(self, num, add):
                self.relayNumber = num
                self.relayAddress = add
                self.pfr = pifacerelayplus.PiFaceRelayPlus(pifacerelayplus.RELAY, self.relayAddress)
                
        def setDetect(self, pin):
                self.pin = pin
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        def toString(self):
                return str('PigGate(' + str(self.relayNumber) + ',' + str(self.relayAddress) + ',' + str(self.pin) + ')')
        
        def open(self):
                self.pfr.relays[self.relayNumber].turn_off()
                self.log('Opened')
        
        def close(self):
                self.pfr.relays[self.relayNumber].turn_on()
                self.log('Closed')
                
        def isOpen(self):
                return GPIO.input(self.pin)
                
        # Disengages, then re-engages the solenoid after a period of 3 seconds
        def switch(self):
                self.close()
                time.sleep(3)
                self.open()
