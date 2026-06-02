#!/bin/bash

set -e

PYTHON_BIN="${PYTHON_BIN:-python3.11}"

cd /home/pi
rm -f nohup.out
nohup "$PYTHON_BIN" -u ./isspointer.py &
