import time
import pifacerelayplus
import os
import threading
import logging
from cv2 import *
from datetime import datetime, date

class PigCamera(object):

        def __init__(self, num = 1, add = 0, IP = '192.168.1.170', user='admin', password='pigbert', port = 80, channel = 1, subtype = 0, maxbytes = 0):
                # Setup Addresses
                self.setRelay(num, add)
                self.cameraIP = IP
                self.cameraPort = port
                self.cameraChannel = channel
                self.cameraSubtype = subtype
                
                #Setup IP Camera url
                self.url = 'rtsp://%s:%s@%s:%i/cam/realmonitor?channel=%i&subtype=%i' % (user, password, IP, port, channel, subtype)

                #Setup Logger
                self.setupLogger()
                self.log('Initiated')
                self.turnOff()
                self.timestamp = 0
                # Setup Image shtuff
                self.sizeLimit = maxbytes
                self.setupImageDir('/home/pi/PigPen/Images')

        def setupLogger(self):
                self.logger = logging.getLogger('PigPen')

        def log(self, stringy):
                self.logger.info('[' + self.toString() + '] ' + stringy)

        def setupImageDir(self, path):
                if not os.path.isdir(path):
                        os.mkdir(path)
                self.path = path

        def toString(self):
                return str('PigCamera(' + str(self.relayNumber) + ',' + str(self.relayAddress) + ',' + str(self.cameraIP) + ')')
        
        ### Image Functions ###
        def grabImage(self, delay = 5):
                self.turnOn()
				
                time.sleep(delay)
				
                counter = 0
                while(counter <= 30):
                        vcap = VideoCapture(self.url)
                        s, img, = vcap.read()
                        if(s):
                            img = resize(img, (960,720))
                            break
                        else:
                            counter += 1
                            time.sleep(1)
                
                
                self.timestamp = time.time()
                localtime = time.localtime(self.timestamp)
                filename = time.strftime('%H:%M:%S-%m:%d:%y', localtime) + '.jpg'
                filepath = os.path.join(self.path, filename)
                imwrite(filepath, img)
                
                self.log('Grabbed image: ' + filename)
                self.turnOff()
                self.cleanupImages()
                
                return filepath
        
        def timeSinceLast(self):
                last = datetime.fromtimestamp(self.timestamp)
                now = datetime.fromtimestamp(time.time())
                return now - last

        def cleanupImages(self):
                self.log('Checking image dir size...')
                files = []
                files = [os.path.join(self.path, file) for file in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, file)) and file[-4:] == '.jpg']
                files.sort(key=lambda x: os.path.getmtime(x))
                size = sum(os.path.getsize(file) for file in files)
                if size > self.sizeLimit and len(files) > 1:
                        self.log('Image dir is too large. Commence trim')
                        while size > self.sizeLimit and len(files) > 1:
                                self.log('Removing: ' + os.path.basename(files[0]))
                                tsize = os.path.getsize(files[0])
                                os.remove(files[0])
                                files.pop(0)
                                size -= tsize
                else:
                        self.log('Image dir is fine')
                
        ### Relay Functions ###
        def setRelayAddress(self, add = 0):
                self.relayAddress = add
                self.pfr = pifacerelayplus.PiFaceRelayPlus(pifacerelayplus.RELAY, self.relayAddress)
                
        def setRelayNumber(self, num = 0):
                self.relayNumber = num
                
        def setRelay(self, num = 0, add = 0):
                self.relayNumber = num
                self.relayAddress = add
                self.pfr = pifacerelayplus.PiFaceRelayPlus(pifacerelayplus.RELAY, self.relayAddress)
                
        def turnOn(self):
                self.pfr.relays[self.relayNumber].turn_on()
                self.log('Turned ON')
                
        def turnOff(self):
                self.pfr.relays[self.relayNumber].turn_off()
                self.log('Turned OFF')
                
        def isOn(self):
                return bool(self.pfr.relays[self.relayNumber].value)
        
        
