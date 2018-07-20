from PigGSM import PigGSM
import time

PigGSM.__init__()
while True:
    try:
        command = input('Enter Command: ')
        PigGSM.write(command)
        time.sleep(0.2)
        print(PigGSM.readAll())
    except (KeyboardInterrupt, SystemExit):
        break
    
