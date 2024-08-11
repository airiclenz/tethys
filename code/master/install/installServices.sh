#!/bin/bash

# Absolute path to this script, e.g. /home/user/username/repos/tethys/code/master/install/install.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/username/repos/tethys/code/master/install
SCRIPTPATH=$(dirname "$SCRIPT")
LENGTH=${#SCRIPTPATH}
ENDPOS=`expr $LENGTH - 8`

# The root directory of the code for the raspberry pi - within the git that is './tethys/code/master'
ROOTPATH=$(echo $SCRIPTPATH| cut -c$1-$ENDPOS)


echo "Root path:  " $ROOTPATH
echo "Script path:" $SCRIPTPATH
cd $SCRIPTPATH

echo ""
echo "================================================================================"
echo "Copying the nginx site configurations now"

sudo cp ./nginx/tethys_api /etc/nginx/sites-available/tethys_api
sudo cp ./nginx/tethys_web /etc/nginx/sites-available/tethys_web

cd /etc/nginx/sites-enabled/

sudo rm tethys_api
sudo rm tethys_web

sudo ln -s /etc/nginx/sites-available/tethys_api
sudo ln -s /etc/nginx/sites-available/tethys_web

echo "Restarting the nginx server"
sudo systemctl restart nginx


echo ""
echo "================================================================================"
echo "(Re-) creating the folder for the correct localized versions of the service descriptions"

cd $ROOTPATH/install/
rm -r services-local
mkdir services-local

cp ./services/tethys-api.service ./services-local/
cp ./services/tethys-core.service ./services-local/
cp ./services/tethys-web.service ./services-local/
cp ./services/tethys-watchdog.service ./services-local/

# -----------------------------------------------------------------------------
echo "Updating the paths in localized versions of the service descriptions"

python3 updateServicePaths.py ./services-local/tethys-api.service $ROOTPATH
python3 updateServicePaths.py ./services-local/tethys-core.service $ROOTPATH
python3 updateServicePaths.py ./services-local/tethys-web.service $ROOTPATH
python3 updateServicePaths.py ./services-local/tethys-watchdog.service $ROOTPATH

# -----------------------------------------------------------------------------
echo "Copying new service definitions to system path /etc/systemd/system"

cd services-local
sudo cp tethys-api.service /etc/systemd/system/tethys-api.service
sudo cp tethys-core.service /etc/systemd/system/tethys-core.service
sudo cp tethys-web.service /etc/systemd/system/tethys-web.service
sudo cp tethys-watchdog.service /etc/systemd/system/tethys-watchdog.service

# -----------------------------------------------------------------------------
echo "Enabling the services"

sudo systemctl enable tethys-api.service
sudo systemctl enable tethys-core.service
sudo systemctl enable tethys-web.service
sudo systemctl enable tethys-watchdog.service

sudo systemctl daemon-reload

# -----------------------------------------------------------------------------
echo "Starting the services"

sudo systemctl start tethys-api.service
sudo systemctl start tethys-core.service
sudo systemctl start tethys-web.service
sudo systemctl start tethys-watchdog.service


# -----------------------------------------------------------------------------
echo "Cleaning up the journals"
sudo journalctl --vacuum-time=1d

###############################################################################
# checking the error log:
# sudo journalctl -u tethys-api.service
# sudo journalctl -u tethys-core.service
# sudo journalctl -u tethys-web.service
# sudo journalctl -u tethys-watchdog.service