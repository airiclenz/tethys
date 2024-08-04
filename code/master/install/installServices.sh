#!/bin/bash

# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
LENGTH=${#SCRIPTPATH}
ENDPOS=`expr $LENGTH - 8`
ROOTPATH=$(echo $SCRIPTPATH| cut -c$1-$ENDPOS)
SOURCEPATH=$(echo $ROOTPATH/src)

echo ""
echo "====================================================================================="
echo "Creating the folder for the local versions of the service descriptions"

rm -r services-local
mkdir services-local


cp ./services/tethys-core.service ./services-local/
cp ./services/tethys-watchdog.service ./services-local/

# -------------------------------------------------------------------------------
echo "Updating the paths in local versions of the service descriptions"

python3 updateServicePaths.py $SOURCEPATH

cd services-local

# -------------------------------------------------------------------------------
echo "Installing and starting the services"

sudo cp tethys-core.service /etc/systemd/system/tethys-core.service
sudo cp tethys-watchdog.service /etc/systemd/system/tethys-watchdog.service

# -------------------------------------------------------------------------------
echo "Enabling the services"

sudo systemctl enable tethys-core.service
sudo systemctl enable tethys-watchdog.service

sudo systemctl daemon-reload

# -------------------------------------------------------------------------------
echo "Starting the services"

sudo systemctl start tethys-core.service
sudo systemctl start tethys-watchdog.service

# checking the error log:
# sudo journalctl -u tethys-core.service
# sudo journalctl -u tethys-watchdog.service