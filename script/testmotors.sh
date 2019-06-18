#!/bin/sh
#
# Example Linux cmd-line script to run the ESP8266 HUZZAH with Stepper Motor
# and Servo
#
# Edit the IP address to point to your ESP8266 IP
# usage:  $ bash ./testmotors.sh
#


# >> CHANGE FOR YOUR ESP8266 IP ADDRESS <<
ESP_IP="192.168.X.X"



# Show Usage
curl http://$ESP_IP/
sleep 1

# Turn on Motors
curl http://$ESP_IP/stepper/start

# Set RPM
curl http://$ESP_IP/stepper/rpm?10

# Turn on external LED and Move it!
curl http://$ESP_IP/led/on
curl http://$ESP_IP/stepper/steps?50
curl http://$ESP_IP/servo/value?45
curl http://$ESP_IP/stepper/steps?50
curl http://$ESP_IP/servo/value?90
curl http://$ESP_IP/stepper/steps?-100
curl http://$ESP_IP/servo/value?0
curl http://$ESP_IP/led/off
sleep 2

# Turn Off Motors
curl http://$ESP_IP/stepper/stop

