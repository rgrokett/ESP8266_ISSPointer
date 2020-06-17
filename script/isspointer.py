#!/usr/bin/env python3
# ISS FLYOVER DETECTION
# This program is part of the ISSPointer:
# https://github.com/rgrokett/ESP8266_ISSPointer
# It runs on a Linux server such as a Raspberry Pi with network connection
# It requires the AltAzPointer project: 
# http://www.instructables.com/id/ESP8266-ISSPointer
# Be sure to edit the USER VARIABLES for your location!
# Note only passes with altitude angles greater than 10deg will point
# 
# Requires:
# sudo apt-get install python3-pip python3-dev
# sudo pip3 install pyephem
#
# Usage:
# nohup python3 -u ./isspointer.py &
#
# Version 0.7 2016.01.16
# Version 2.0 2019.06.16 - Python3 update
#     license: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html
#

try:
   import ephem    
except:
   print("Requires sudo pip3 install pyephem")
   exit()

import calendar
import datetime
import time
import math
import urllib.request, urllib.error, urllib.parse
import socket
import atexit
import sys


############ USER VARIABLES
DEBUG = 1       # 0 off 1 on
INFO  = 1       # Display ephemeris info 

# YOUR LOCATION
LAT = 30.1  # Your Latitude (+N) deg
LON = -81.8 # Your Longitude (+E) deg
ELV = 11.0  # Elevation at your location (meters)

# FOR ALT/AZ POINTER 
STEPIP = "http://192.168.X.X/" # IP Address of YOUR ESP8266 AltAZ Pointer
STEPS  = 200    # Replace with your stepper (steps per one revolution)

########### END OF USER VARIABLES

# Global Consts
FLOAT_A = float(STEPS)/360.0
HOR = 10.0  # Default to 10 degrees above horizon before being "visible"
TLE = "https://api.wheretheiss.at/v1/satellites/25544/tles?format=text"

# Global Variables
glob_tle = []           # used for ISS TLE data
glob_azOld   = 0        # used to find diff between old and new AZ
glob_azReset = 0        # used to reset pointer north at end of run


def getTLE():
    global glob_tle
    try:
        resp = urllib.request.urlopen(TLE)
        glob_tle = resp.read().decode('utf-8').split('\n')
        if DEBUG:
          print (glob_tle)
    except Exception as ex:
        print("ERROR: Cannot retrieve coordinate data, retrying...")
        if DEBUG:
          print(ex)
        time.sleep(60)
         

# CONTROL LED
def doLED(state):
    ledUrl = STEPIP
    try:
        cmd = ledUrl+"led/"+str(state)
        resp = urllib.request.urlopen(cmd)
        if DEBUG:
           print (cmd)
           print(resp.read())
        resp.close()
        time.sleep(0.1) # keep from overflowing ESP wifi buffer
    except:
        print("ERROR: LED comm failure")

# CONTROL AZIMUTH STEPPER MOTOR
def doStepper(steps):
    if (steps == 0):
        return
    try:
       stepperUrl = STEPIP
       cmd = stepperUrl+"stepper/start"
       resp = urllib.request.urlopen(cmd)
       if DEBUG:
           print (cmd)
           print(resp.read())
       resp.close()
       time.sleep(0.1) # keep from overflowing ESP wifi buffer
       cmd = stepperUrl+"stepper/rpm?10"
       resp = urllib.request.urlopen(cmd)
       if DEBUG:
           print (cmd)
           print(resp.read())
       resp.close()
       time.sleep(0.1) # keep from overflowing ESP wifi buffer
       cmd = stepperUrl+"stepper/steps?"+str(steps)
       resp = urllib.request.urlopen(cmd)
       if DEBUG:
           print (cmd)
           print(resp.read())
       resp.close()
       time.sleep(0.1) # keep from overflowing ESP wifi buffer
       cmd = stepperUrl+"stepper/stop"
       resp = urllib.request.urlopen(cmd)
       if DEBUG:
           print (cmd)
           print(resp.read())
       resp.close()
       time.sleep(0.1) # keep from overflowing ESP wifi buffer
    except:
       time.sleep(5)
       try:
           cmd = stepperUrl+"stepper/stop"
           resp = urllib.request.urlopen(cmd)
           print (cmd)
           print(resp.read())
           resp.close()
       except:
           print("Stepper comm failure")

# CONTROL ALTITUDE SERVO
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
           print (cmd)
           print(resp.read())
        resp.close()
        time.sleep(0.1) # keep from overflowing ESP wifi buffer
    except:
        print("Servo comm failure")

# CONTROL RESET TO NORTH & LEVEL POSITION
def doAzReset():
    # Reset back to point north
    global glob_azOld
    global glob_azReset
    glob_azOld   = 0
    if DEBUG:
        print(("doAzReset("+str(glob_azReset)+")"))
    if (glob_azReset != 0):
        steps = glob_azReset
        time.sleep(0.2)
        doStepper(-steps)
        glob_azReset = 0
        doServo(0)
        doLED('off')
    return


def exit():
    """
    Exit handler, which clears all custom chars and shuts down the display.
    """
    try:
        print("EXITING")  
    except:
        # avoids ugly KeyboardInterrupt trace on console...
        pass


#####
# MAIN HERE
if __name__ == '__main__':
  atexit.register(exit)

  # timeout in seconds
  timeout = 10
  socket.setdefaulttimeout(timeout)

  if DEBUG:
      print("DEBUG MODE")

  # This is to allow getting the TLE after restarts
  pt = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    
  duration = 0        # Duration of a flyover in seconds

  while True:
    print("\n")
    print("ISS PASS INFO")

    # Get TLE Info only every 20 minutes
    # just left math for clarity, not speed
    ct = datetime.datetime.utcnow()
    next_seconds = int((ct - pt).total_seconds())
    if DEBUG:
      print(("Seconds since last TLE check: %s" % next_seconds))
    if (next_seconds > (20 * 60)):
        getTLE()    
        pt = ct

    iss = ephem.readtle(glob_tle[0], glob_tle[1], glob_tle[2]);
    site = ephem.Observer()
    site.date = datetime.datetime.utcnow()
    site.lat = str(LAT)
    site.lon = str(LON)
    site.horizon = str(HOR)
    site.elevation = ELV
    site.pressure = 0

    lt = ephem.localtime(site.date)
    lt = lt.replace(microsecond=0)
    print("Current UTC time    : %s" % site.date)
    print("Current Local time  : %s" % lt)

    # FIND NEXT PASS INFO JUST FOR REFERENCE
    tr, azr, tt, altt, ts, azs = site.next_pass(iss)
    if DEBUG:
         print("tr=%s  ts=%s" % (tr,ts))

    if (str(tr) == 'None'):
        continue

    if (ts > tr):
        duration = int((ts - tr) *60*60*24)
        lt = ephem.localtime(tr)
        lt = lt.replace(microsecond=0)
        print(("Next Pass Local time: %s" % lt))
        print("")
        if INFO:
            print(("UTC Rise Time   : %s" % tr))
            print(("UTC Max Alt Time: %s" % tt))
            print(("UTC Set Time    : %s" % ts))
            print(("Rise Azimuth: %s" % azr))
            print(("Set Azimuth : %s" % azs))
            print(("Max Altitude: %s" % altt))
            print(("Duration    : %s" % duration))

    # FIND THE CURRENT LOCATION OF ISS
    iss.compute(site)
    degrees_per_radian = 180.0 / math.pi

    altDeg = int(iss.alt * degrees_per_radian)
    azDeg = int(iss.az * degrees_per_radian)
    iss.compute(ct)
    if INFO:
      print()
      print("CURRENT LOCATION:")
      print(("Latitude : %s" % iss.sublat))
      print(("Longitude: %s" % iss.sublong))
      print(("Azimuth  : %s" % azDeg))
      print(("Altitude : %s" % altDeg))
  
    # IS ISS VISIBLE NOW
    if ( altDeg > int(HOR) ):
      if INFO:
        print("ISS IS VISIBLE")

      if ( altDeg > int(45) ):
        if INFO:
          print("ISS IS OVERHEAD")

      next_check = 5        

      # Send to AltAz Pointer
      doLED('on')

      # Point Servo towards ISS
      # Convert AZ deg to 200 steps
      # Find the difference between current location and new location
      azDiff = azDeg - glob_azOld
      glob_azOld  = azDeg
      steps = int(float(azDiff) * FLOAT_A)
      doStepper(steps)
      glob_azReset += steps
      doServo(altDeg)
    else:
      if INFO:
          print("ISS below horizon")
      doAzReset()
      next_check = 60

    time.sleep(next_check)
  # END WHILE

