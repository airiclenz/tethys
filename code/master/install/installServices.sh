#!/bin/bash
set -e  # Exit on error

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


echo ""
echo "================================================================================"
echo -e "${YELLOW}Setting up the nginx configuration now...${NOCOLOR}"
echo ""

cd $SCRIPTPATH

# -------------------------------------
echo "Re-creating the localized asset folder"
rm -rf assets-localized && mkdir -p assets-localized

# -------------------------------------
echo "Copying the nginx configurations to the localized asset folder"

cp ./assets/tethys-{api,web}.nginx ./assets-localized/

# -------------------------------------
echo "Updating the paths in the nginx configurations"

for file in ./assets-localized/tethys-{api,web}.nginx; do
    python3 updateTokenInFile.py "$file" "{TETHYS-PATH}" "$ROOTPATH"
    python3 updateTokenInFile.py "$file" "{HOST-NAME}" "$HOSTNAME"
done

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

sudo chown -R www-data:www-data "$WWWPATH/tethys/staticcollect"
sudo chmod -R u=rwX,g=rX,o=rX "$WWWPATH/tethys/staticcollect"

echo ""
echo "================================================================================"
echo -e "${YELLOW}Preparing the wesocket folders${NOCOLOR}"
echo ""

sudo mkdir -p /ws/
sudo chown www-data:www-data /ws/
sudo chmod 770 /ws/

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

for service in tethys-{api,core,web,watchdog} daphne; do
    python3 ./install/updateTokenInFile.py "./install/assets-localized/$service.service" "{TETHYS-PATH}" "$ROOTPATH"
done

python3 ./install/updateTokenInFile.py ./install/assets-localized/gunicorn_config_api.py {TETHYS-PATH} $ROOTPATH
python3 ./install/updateTokenInFile.py ./install/assets-localized/gunicorn_config_web.py {TETHYS-PATH} $ROOTPATH

# -------------------------------------
echo "Copying new service definitions to system path /etc/systemd/system and enabling services..."

for service in tethys-{api,core,web,watchdog} daphne; do
    sudo cp "./install/assets-localized/$service.service" "/etc/systemd/system/$service.service"
    sudo systemctl enable "$service.service"
    printf " > Enabled %s\n" "$service.service"
done

sudo systemctl daemon-reload

# -------------------------------------
# Start - or Restart all services
cd $SCRIPTPATH
./services-restart.sh

echo ""
# -------------------------------------
echo "Restarting the nginx server"
sudo systemctl restart nginx

echo ""
echo "================================================================================"

echo ""
echo -e "${GREEN}The Tethys-services were installed.${NOCOLOR}"
echo ""

