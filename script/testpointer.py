#!/usr/bin/env python
# 
# Example program to simulate a (fast!) flyover
# 
# usage: $ python testPointer.py
#

import urllib.request, urllib.error, urllib.parse
import time

### USER EDIT
STEPIP = "http://192.168.1.71/" # REPLACE with your IP of ESP8266
STEPS  = 200    # REPLACE with your stepper number of steps per revolution
### END USER EDIT


# Global Variables (simplistic coding!)
glob_azOld   = 0        # used to find diff between old and new AZ
glob_azReset = 0        # used to reset pointer north at end of run

DEBUG = 1	# Display status msgs

# Global Consts 
FLOAT_A = float(STEPS)/360.0

# Hacked together from original program
def doStepper(steps):
    if (steps == 0):
        return
    try:
       stepperUrl = STEPIP
       cmd = stepperUrl+"stepper/start"
       resp = urllib.request.urlopen(cmd)
       time.sleep(0.2)
       if DEBUG:
           print(resp.read().decode('utf-8'))
       resp.close()
       cmd = stepperUrl+"stepper/rpm?10"
       resp = urllib.request.urlopen(cmd)
       time.sleep(0.2)
       if DEBUG:
           print(resp.read().decode('utf-8'))
       resp.close()
       cmd = stepperUrl+"stepper/steps?"+str(steps)
       resp = urllib.request.urlopen(cmd)
       time.sleep(0.2)
       if DEBUG:
           print(resp.read().decode('utf-8'))
       resp.close()
       cmd = stepperUrl+"stepper/stop"
       resp = urllib.request.urlopen(cmd)
       time.sleep(0.2)
       if DEBUG:
           print(resp.read().decode('utf-8'))
       resp.close()
    except:
       time.sleep(5)
       try:
           cmd = stepperUrl+"stepper/stop"
           resp = urllib.request.urlopen(cmd)
           print(resp.read().decode('utf-8'))
           resp.close()
       except:
           print("Stepper comm failure")

def doServo(angle):
    if (angle < 0 ):
        angle = 0
    if (angle > 90 ):
        angle = 90
    servoUrl = STEPIP
    try:
        cmd = servoUrl+"servo/value?"+str(angle)
        resp = urllib.request.urlopen(cmd)
        if DEBUG:
           print(resp.read().decode('utf-8'))
        resp.close()
    except:
        print("Servo comm failure")

def doLED(state):
    ledUrl = STEPIP
    try:
        cmd = ledUrl+"led?"+str(state)
        resp = urllib.request.urlopen(cmd)
        if DEBUG:
           print(resp.read().decode('utf-8'))
        resp.close()
    except:
        print("LED comm failure")


def doAzReset():
    # Reset back to point north
    global glob_azOld
    global glob_azReset
    glob_azOld   = 0
    print(("doAzReset("+str(glob_azReset)+")"))
    if (glob_azReset != 0):
        steps = glob_azReset
        doStepper(-steps)
        time.sleep(0.5)
        glob_azReset = 0
        doServo(0)
        time.sleep(0.5)
        doLED('off')


# MAIN
alt = 0
elev= 1
doLED('on')
for az in range(200,40, -5):
   if (elev):
       alt += 5
       if (alt > 75):
            alt = 75
            elev = 0
   else:
        alt -= 5
        if (alt < 0 ):
            alt = 0

   azDiff = az - glob_azOld
   glob_azOld = az
   steps = int(float(azDiff) * FLOAT_A)

   print(("altDeg="+str(alt)))
   print(("azDeg="+str(az)))
   print(("steps="+str(steps)))

   doStepper(steps)
   time.sleep(0.5)
   glob_azReset += steps
   doServo(alt)
   time.sleep(0.5)
# end for 
doAzReset()
print("FINISHED")

