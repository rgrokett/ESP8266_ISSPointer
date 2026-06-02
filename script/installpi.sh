#!/bin/sh
# Simple install script
# FOR RASPBERRY PI VERSION ONLY

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(dirname -- "$SCRIPT_DIR")

if command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN=python3.11
else
  echo "python3.11 was not found; install Python 3.11 before running isspointer.py"
  exit 1
fi

cp "$SCRIPT_DIR/isspointer2.py" /home/pi/isspointer.py
cp "$SCRIPT_DIR/run.sh" /home/pi/run.sh
cp -rp "$PROJECT_DIR/sounds" /home/pi

echo "Using $PYTHON_BIN"

echo "Append the following line to /etc/rc.local before the exit 0"
echo "/bin/sh /home/pi/run.sh"
