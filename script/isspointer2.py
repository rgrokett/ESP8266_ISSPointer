#!/usr/bin/env python3
#
# ISS FLYOVER DETECTION
# LCD DISPLAY & SOUND VERSION FOR RASPBERRY PI
#
#
# Displays next time ISS is visible
# For Raspberry Pi with Audio and LCD Alerts with ISS is overhead
#
# Be sure to edit the USER VARIABLES for your location!
# Note only passes with altitude angles greater than 10deg will point
# 
# Requires:
# Raspi with Adafruit 16x2 LCD Display and external audio spkr
# AltAz Pointer https://github.com/rgrokett/ESP8266_ISSPointer
#           See http://www.instructables.com/id/ESP8266-ISSPointer
# Install Adafruit LCD lib & dependencies from 
#    https://github.com/adafruit/Adafruit_Python_CharLCD
# Also install:
# $ sudo apt-get install python3-pip python3-dev
# $ sudo pip3 install pyephem
#
# Usage:
# $ sudo nohup python3 -u ./isspointer.py &
#
# Version 1.4 2016.01.11 - added extra error handling
# Version 2.0 2019.06.16 - Python3 update
# Version 2.1 2020.03.21 - Update LCD libraries
#     license: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html
#

try:
   import ephem
except Exception as ex:
   print("Requires sudo pip3 install pyephem")
   exit()

import subprocess
import calendar
import datetime
import time
import math
import urllib.request, urllib.error, urllib.parse
import socket
import atexit
import sys

LCD = 0 # Default to no LCD
try:
    import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
    import board
    import busio
    lcd_columns = 16
    lcd_rows = 2
    i2c = busio.I2C(board.SCL, board.SDA)
    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
    LCD = 1
except Exception as ex:
    print("No LCD Display Found. Ignored...")
    print(ex)
    

############ USER VARIABLES
DEBUG = 1       # 0 off 1 on
INFO  = 1       # Display ephemeris info 

# YOUR LOCATION
LAT = 30.1  # Your Latitude (+N) deg
LON = -81.8 # Your Longitude (+E) deg
ELV = 11.0  # Elevation at your location (meters)

# FOR ALT/AZ POINTER 
STEPIP = "http://192.168.1.71/" # IP Address of YOUR ESP8266 AltAZ Pointer
STEPS  = 200    # Replace with your stepper (steps per one revolution)

AUDIO = 1 # 0 off 1 on
QUIET = [ 00, 0o7 ] # Don't play audio between midnight & 7:59AM
PATH = "/home/pi/sounds/"  # Path to Sound files

########### END OF USER VARIABLES

# Global Consts
FLOAT_A = float(STEPS)/360.0
HOR = 10.0  # Default to 10 degrees above horizon before being "visible"
TLE = "https://api.wheretheiss.at/v1/satellites/25544/tles?format=text"
SOUND = [ 0, "2001buzz.wav","2001ping.wav","2001function.wav","2001alarm.wav" ]

# Global Variables
glob_tle = []           # used for ISS TLE data
glob_azOld   = 0        # used to find diff between old and new AZ
glob_azReset = 0        # used to reset pointer north at end of run

## METHODS

def sound(val): # Play a sound
    time.sleep(1)
    sndfile = PATH+SOUND[val]
    proc = subprocess.call(['/usr/bin/aplay', sndfile], stderr=subprocess.PIPE)
    return

def isQuiet():  # Quiet time no sound
  if AUDIO:
    hour = time.strftime('%H')
    if int(hour) >= QUIET[0] and int(hour) < QUIET[1]:
         return(1)
    else:
         return(0)
  return(1)

def next_visible(risetime): # LCD Display dates/times
        lt = ephem.localtime(risetime)
        lt = lt.replace(microsecond=0)
        dt = datetime.datetime.strptime(str(lt), "%Y-%m-%d %H:%M:%S")
        v = dt.strftime('%m/%d %X')
        c = time.strftime('%m/%d %X')
        if LCD:
          lcd.clear()
          lcd.color = [100, 0, 0]
          message = ("NEXT:" + v)
          message += ("\n")
          message += ("Time:" + c)
          lcd.message = message

def flash_display():    # LCD Display flash
        lcd.color = [0, 0, 0]
        time.sleep(0.4)
        lcd.color = [100, 0, 0]
        time.sleep(0.4)
        lcd.color = [0, 0, 0]
        time.sleep(0.4)
        lcd.color = [100, 0, 0]
        time.sleep(0.4)
        lcd.color = [0, 0, 0]
        time.sleep(0.4)
        lcd.color = [100, 0, 0]

# GET ISS ORBIT DATA
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
    return

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
    return

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
       print("Unexpected doStepper() error:", sys.exc_info()[0])
       time.sleep(1)
       try:
           cmd = stepperUrl+"stepper/stop"
           resp = urllib.request.urlopen(cmd)
           print (cmd)
           print(resp.read())
           resp.close()
           time.sleep(0.1) # keep from overflowing ESP wifi buffer
       except:
           print("Stepper comm failure")
    return

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
        lcd = Adafruit_CharLCDPlate()
        lcd.backlight = False
        lcd.color = [0, 0, 0]
        clearChars(lcd)
        lcd.stop()
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

    if LCD:
      lcd.clear()
      lcd.backlight = True
      lcd.color = [100, 0, 0]
      lcd.message = "ISS STARTUP"
      lcd.message = "\n LCD version"
      flash_display()
    sound(3)
    time.sleep(3)
    if LCD:
      lcd.clear()

    if DEBUG:
        print("DEBUG MODE")

    # This is to allow getting the TLE after restarts
    pt = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

    duration = 0  # Duration of a flyover in seconds
    
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
        if LCD:
          lcd.clear()
          lcd.backlight = True
          lcd.color = [100, 0, 0]
        # IS ISS OVERHEAD (ABOVE 45 DEG) OR JUST VISIBLE (10deg to 45deg)
        if ( altDeg > int(45) ):  
          if INFO:
            print("ISS IS OVERHEAD")
          if LCD:
            lcd.message = ("ISS IS OVERHEAD")
            flash_display()
          if (not isQuiet()):
            if (altDeg > int(60)):
              sound(4)
          else:
              sound(2)
              sound(2)
              sound(2)
        else:
          if INFO:
            print("ISS IS VISIBLE")
          if LCD:
            lcd.message = ("ISS IS VISIBLE")
            lcd.message = ("\nDuration:" + str(duration) + "sec")
            flash_display()
          if (not isQuiet()):
              sound(1)
              sound(1)
              sound(1)
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
          next_visible(tr)
          next_check = 60

      # Turn off LCD backlight during quiet time 
      # except when ISS visible
      if not isQuiet():
          if LCD:
            lcd.backlight = True
            lcd.color = [100, 0, 0]
      else:
          if LCD:
            lcd.backlight = False
            lcd.color = [0, 0, 0]

      time.sleep(next_check)
    # END WHILE

