#!/bin/bash

# Absolute path to this script, e.g. /home/user/username/repos/tethys/code/master/install/install.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/username/repos/tethys/code/master/install
SCRIPTPATH=$(dirname "$SCRIPT")
LENGTH=${#SCRIPTPATH}
ENDPOS=`expr $LENGTH - 8`
# The root directory of the code for the raspberry pi - within the git that is './tethys/code/master'
ROOTPATH=$(echo $SCRIPTPATH| cut -c$1-$ENDPOS)
WWWPATH='/var/www'


echo ""
echo "=====  STARTING the installation of TETHYS  ===================================="
echo ""
echo "Root path:  " $ROOTPATH
echo "Script path:" $SCRIPTPATH

cd $SCRIPTPATH

sudo rm -r assets-localized
mkdir assets-localized


echo ""
echo "================================================================================"
echo "Setting up the nginx configuration now..."

# -------------------------------------
echo "Copying the nginx configurations to the localized folder"

cp ./assets/tethys-api.nginx ./assets-localized/
cp ./assets/tethys-web.nginx ./assets-localized/

# -------------------------------------
echo "Updating the paths in the nginx configurations"

python3 updateTokenInFile.py ./assets-localized/tethys-api.nginx {TETHYS-PATH} $ROOTPATH
python3 updateTokenInFile.py ./assets-localized/tethys-web.nginx {TETHYS-PATH} $ROOTPATH

# -------------------------------------
echo "Copying localized versins to the nginx system directory"

sudo cp ./assets-localized/tethys-api.nginx /etc/nginx/sites-available/tethys-api
sudo cp ./assets-localized/tethys-web.nginx /etc/nginx/sites-available/tethys-web

# -------------------------------------
echo "Creating sys-links in sites-enabled"

cd /etc/nginx/sites-enabled/

sudo rm tethys-api
sudo rm tethys-web

sudo ln -s /etc/nginx/sites-available/tethys-api
sudo ln -s /etc/nginx/sites-available/tethys-web


echo ""
echo "================================================================================"
echo "Collecting static files and changing file permissions for nginx"

echo "Copying the static folder to staticcollect"
sudo mkdir -p $WWWPATH/tethys/
sudo chmod 755 $WWWPATH/tethys/

cd $WWWPATH/tethys/
sudo rm -r /staticcollect
sudo mkdir staticcollect

sudo cp -r $ROOTPATH/web/static/css $WWWPATH/tethys/staticcollect/css
sudo cp -r $ROOTPATH/web/static/fonts $WWWPATH/tethys/staticcollect/fonts
sudo cp -r $ROOTPATH/web/static/images $WWWPATH/tethys/staticcollect/images
sudo cp -r $ROOTPATH/web/static/js $WWWPATH/tethys/staticcollect/js

echo "Giving nginx access to staticcollect"
sudo chmod -R 755 $WWWPATH/tethys/staticcollect/
sudo chown -R www-data:www-data $WWWPATH/tethys/staticcollect/


echo ""
echo "================================================================================"
echo "Installing our customn system services (api, core, web, watchdog)"

cd $SCRIPTPATH

cp ./assets/tethys-api.service ./assets-localized/
cp ./assets/tethys-core.service ./assets-localized/
cp ./assets/tethys-web.service ./assets-localized/
cp ./assets/tethys-watchdog.service ./assets-localized/

# -------------------------------------
echo "Updating the paths in localized versions of the service descriptions"

python3 updateTokenInFile.py ./assets-localized/tethys-api.service {TETHYS-PATH} $ROOTPATH
python3 updateTokenInFile.py ./assets-localized/tethys-core.service {TETHYS-PATH} $ROOTPATH
python3 updateTokenInFile.py ./assets-localized/tethys-web.service {TETHYS-PATH} $ROOTPATH
python3 updateTokenInFile.py ./assets-localized/tethys-watchdog.service {TETHYS-PATH} $ROOTPATH

# -------------------------------------
echo "Copying new service definitions to system path /etc/systemd/system"

sudo cp ./assets-localized/tethys-api.service /etc/systemd/system/tethys-api.service
sudo cp ./assets-localized/tethys-core.service /etc/systemd/system/tethys-core.service
sudo cp ./assets-localized/tethys-web.service /etc/systemd/system/tethys-web.service
sudo cp ./assets-localized/tethys-watchdog.service /etc/systemd/system/tethys-watchdog.service

# -------------------------------------
echo "Enabling the services"

sudo systemctl enable tethys-api.service
sudo systemctl enable tethys-core.service
sudo systemctl enable tethys-web.service
sudo systemctl enable tethys-watchdog.service

sudo systemctl daemon-reload

# -------------------------------------
echo "Starting the services"

sudo systemctl start tethys-api.service
sudo systemctl start tethys-core.service
sudo systemctl start tethys-web.service
sudo systemctl start tethys-watchdog.service


# -------------------------------------
echo "Restarting the nginx server"

sudo systemctl restart nginx


echo ""
echo "================================================================================"
echo "Cleaning up the journals"

sudo journalctl --vacuum-time=1d


###############################################################################
# checking the error log:
# sudo journalctl -u tethys-api.service
# sudo journalctl -u tethys-core.service
# sudo journalctl -u tethys-web.service
# sudo journalctl -u tethys-watchdog.service