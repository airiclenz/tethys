#!/bin/bash

# Default value for DEBUG
DEBUG=true

# Absolute path to this script, e.g. /home/user/username/repos/tethys/code/master/install/install.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/username/repos/tethys/code/master/install
SCRIPTPATH=$(dirname "$SCRIPT")
# The root directory of the code for the raspberry pi - within the git that is './tethys/code/master'
ROOTPATH=$(dirname "$SCRIPTPATH")

WWWPATH='/var/www'
HOSTNAME=$(hostname -s)'.local'

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NOCOLOR='\033[0m' # No Color


# Parse command-line arguments
for arg in "$@"
do
  case $arg in
    --debug=*)
      DEBUG="${arg#*=}"
      shift # Remove --debug= from processing
      ;;
    *)
      # Unknown option
      ;;
  esac
done


echo ""
echo -e "${YELLOW}=====  STARTING the installation of TETHYS services ============================${NOCOLOR}"
echo ""
echo "Debug mode is set to: $DEBUG"

cd $SCRIPTPATH

sudo rm -r assets-localized
mkdir assets-localized


echo ""
echo "================================================================================"
echo -e "${YELLOW}Setting up the nginx configuration now...${NOCOLOR}"
echo ""

# -------------------------------------
echo "Copying the nginx configurations to the localized folder"

cp ./assets/tethys-api.nginx ./assets-localized/
cp ./assets/tethys-web.nginx ./assets-localized/

# -------------------------------------
echo "Updating the paths in the nginx configurations"

python3 updateTokenInFile.py ./assets-localized/tethys-api.nginx {TETHYS-PATH} $ROOTPATH
python3 updateTokenInFile.py ./assets-localized/tethys-api.nginx {HOST-NAME} $HOSTNAME
python3 updateTokenInFile.py ./assets-localized/tethys-web.nginx {TETHYS-PATH} $ROOTPATH
python3 updateTokenInFile.py ./assets-localized/tethys-web.nginx {HOST-NAME} $HOSTNAME

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
echo -e "${YELLOW}Collecting static files and changing file permissions for nginx${NOCOLOR}"
echo ""

echo "Copying the static folder to staticcollect"
sudo mkdir -p $WWWPATH/tethys/
sudo chmod 755 $WWWPATH/tethys/

cd $WWWPATH/tethys/
sudo rm -r ./staticcollect
sudo mkdir staticcollect

sudo cp -r $ROOTPATH/web/static/css $WWWPATH/tethys/staticcollect/css
sudo cp -r $ROOTPATH/web/static/fonts $WWWPATH/tethys/staticcollect/fonts
sudo cp -r $ROOTPATH/web/static/images $WWWPATH/tethys/staticcollect/images
sudo cp -r $ROOTPATH/web/static/js $WWWPATH/tethys/staticcollect/js
sudo cp -r $ROOTPATH/web/static/templatter $WWWPATH/tethys/staticcollect/templatter

if [ $DEBUG == "true" ]; then
    sudo cp -r $ROOTPATH/web/static/ts $WWWPATH/tethys/staticcollect/ts
fi

echo "Giving nginx access to staticcollect"
sudo chmod -R 755 $WWWPATH/tethys/staticcollect/
sudo chown -R www-data:www-data $WWWPATH/tethys/staticcollect/

echo ""
echo "================================================================================"
echo -e "${YELLOW}Preparing the wesocket folders${NOCOLOR}"
echo ""

sudo mkdir -p /ws/
#todo - assign to user that is running daphne
#sudo chown <your_user>:<your_group> /ws/
sudo chmod 757 /ws/

echo "Done"


if [ $DEBUG == "true" ]; then

    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Cleaning up the journals${NOCOLOR}"
    echo ""

    cd $SCRIPTPATH
    ./services-clearLogs.sh

fi


echo ""
echo "================================================================================"
echo -e "${YELLOW}Installing our customn system services (api, core, web, watchdog, daphne)${NOCOLOR}"
echo ""

cd $ROOTPATH

cp ./install/assets/tethys-api.service ./install/assets-localized/
cp ./install/assets/tethys-core.service ./install/assets-localized/
cp ./install/assets/tethys-web.service ./install/assets-localized/
cp ./install/assets/tethys-watchdog.service ./install/assets-localized/

cp ./install/assets/daphne.service ./install/assets-localized/

cp ./api/config/gunicorn.py ./install/assets-localized/gunicorn_config_api.py
cp ./web/config/gunicorn.py ./install/assets-localized/gunicorn_config_web.py

# -------------------------------------
echo "Updating the paths in localized versions of the service descriptions"

python3 ./install/updateTokenInFile.py ./install/assets-localized/tethys-api.service {TETHYS-PATH} $ROOTPATH
python3 ./install/updateTokenInFile.py ./install/assets-localized/tethys-core.service {TETHYS-PATH} $ROOTPATH
python3 ./install/updateTokenInFile.py ./install/assets-localized/tethys-web.service {TETHYS-PATH} $ROOTPATH
python3 ./install/updateTokenInFile.py ./install/assets-localized/tethys-watchdog.service {TETHYS-PATH} $ROOTPATH
python3 ./install/updateTokenInFile.py ./install/assets-localized/daphne.service {TETHYS-PATH} $ROOTPATH

python3 ./install/updateTokenInFile.py ./install/assets-localized/gunicorn_config_api.py {TETHYS-PATH} $ROOTPATH
python3 ./install/updateTokenInFile.py ./install/assets-localized/gunicorn_config_web.py {TETHYS-PATH} $ROOTPATH

# -------------------------------------
echo "Copying new service definitions to system path /etc/systemd/system"

sudo cp ./install/assets-localized/tethys-api.service /etc/systemd/system/tethys-api.service
sudo cp ./install/assets-localized/tethys-core.service /etc/systemd/system/tethys-core.service
sudo cp ./install/assets-localized/tethys-web.service /etc/systemd/system/tethys-web.service
sudo cp ./install/assets-localized/tethys-watchdog.service /etc/systemd/system/tethys-watchdog.service
sudo cp ./install/assets-localized/daphne.service /etc/systemd/system/daphne.service

# -------------------------------------
echo ""
echo "Enabling the services"

sudo systemctl enable tethys-api.service
echo " > Enabled tethys-api.service"

sudo systemctl enable tethys-core.service
echo " > Enabled tethys-core.service"

sudo systemctl enable tethys-web.service
echo " > Enabled tethys-web.service"

sudo systemctl enable tethys-watchdog.service
echo " > Enabled tethys-watchdog.service"

sudo systemctl enable daphne.service
echo " > Enabled daphne.service"

sudo systemctl daemon-reload

# -------------------------------------
echo ""
echo "Starting the services"

sudo systemctl start tethys-api.service
echo " > Started tethys-api.service"

sudo systemctl start tethys-core.service
echo " > Started tethys-core.service"

sudo systemctl start tethys-web.service
echo " > Started tethys-web.service"

sudo systemctl start tethys-watchdog.service
echo " > Started tethys-watchdog.service"

sudo systemctl start daphne.service
echo " > Started daphne.service"

echo ""
# -------------------------------------
echo "Restarting the nginx server"
sudo systemctl restart nginx

echo ""
echo "================================================================================"

echo ""
echo -e "${GREEN}The Tethys-services were installed.${NOCOLOR}"
echo ""

