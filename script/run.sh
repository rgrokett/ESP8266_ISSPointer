#!/bin/bash

cd /home/pi/ISS
sudo rm nohup.out
#sudo nohup python -u ./iss_overhead.py &
#sudo nohup python -u ./isspointer.py &
sudo nohup python -u ./isspointer2.py &

