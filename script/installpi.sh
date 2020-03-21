#!/bin/sh
# Simple install script
# FOR RASPBERRY PI VERSION ONLY

cp isspointer2.py /home/pi/isspointer.py
cp run.sh /home/pi/run.sh
cd ..
cp -rp ./sounds /home/pi

echo "Append the following line to /etc/rc.local before the exit 0"
echo "/bin/sh /home/pi/run.sh"

