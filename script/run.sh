#!/bin/bash

cd /home/pi
sudo rm nohup.out
sudo nohup python3 -u ./isspointer.py &

