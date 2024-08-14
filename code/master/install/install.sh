#!/bin/bash

DEBUG=true
REBOOTED=false

# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
# The root directory of the code for the raspberry pi - within the git that is './tethys/code/master'
ROOTPATH=$(dirname "$SCRIPTPATH")

VENV_NAME="env_tethys"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NOCOLOR='\033[0m' # No Color


# Parse command-line arguments
for arg in "$@"
do
  case $arg in
    --rebooted=*)
      REBOOTED="${arg#*=}"
      shift # Remove --debug= from processing
      ;;
    *)
      # Unknown option
      ;;
  esac
done


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
code_pre_reboot() {

    echo "================================================================================"
    echo ""
    echo -e "${RED}This script will restart the computer. ${YELLOW}Do you want to continue?${NOCOLOR}"
    echo ""
    echo -e "[ ${GREEN}yes${NOCOLOR} / ${RED}no${NOCOLOR} ]"
    echo ""
    read answer

    if [ "$answer" != "${answer#[Yy]}" ] ;then
        echo "Proceeding..."
        # Place the commands you want to execute here
    else
        echo "Aborting..."
        exit 1
    fi

    clear
    echo -e "${YELLOW}=====  STARTING the installation of ${GREEN}TETHYS${YELLOW}  ====================================${NOCOLOR}"
    echo ""
    echo "Root path:  " $ROOTPATH
    echo "Script path:" $SCRIPTPATH

    cd $ROOTPATH


    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Running a system update / upgrade${NOCOLOR}"
    echo ""

    sudo apt update -y
    sudo apt full-upgrade -y

    # needed for virtual environments (if not yet installed)
    sudo apt install python3-venv python3-full -y
    # this is needed for the later installation of the python lib RPi.GPIO
    sudo apt install python3-dev -y
    # needed for numpy on the Raspberry Pi
    sudo apt install libopenblas-dev -y
    # webserver for hosting our* django apps
    sudo apt install nginx -y
    # the redis server used for the websocket functionality
    sudo apt install redis-server -y
    # used for formatting json
    sudo apt install jq -y

    # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #   P Y T H O N - V E N V
    # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Setting up the python environment${NOCOLOR}"
    echo ""

    if [ ! -d $VENV_NAME ]; then
        echo $VENV_NAME "does not exist -> creating it now..."
        python3 -m venv $VENV_NAME
    else
        echo $VENV_NAME " already exists."
    fi

    source $VENV_NAME/bin/activate
    echo "The virtual environment" $VENV_NAME "was activated."

    echo "Updating the pip installer."
    python3 -m pip install --upgrade pip

    echo "Installing needed packages now..."
    pip install -r ./install/python-requirements.txt



    # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #   M I G R A T I O N S
    # :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Handling django migrations now...${NOCOLOR}"
    echo ""

    echo "API:"
    cd $ROOTPATH/api
    python manage.py makemigrations tethys_api
    python manage.py migrate

    echo ""
    echo "WEB:"
    cd $ROOTPATH/web
    python manage.py makemigrations tethys_web
    python manage.py migrate

    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Enabling SPI, Redis-Server${NOCOLOR}"
    echo ""

    cd $ROOTPATH/install

    # enable SPI
    sudo python3 enableSpi.py
    sudo systemctl enable redis-server


    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Calling sub-script for installation of the services...${NOCOLOR}"
    echo ""

    # run the service install script
    ./installServices.sh --debug=$DEBUG


    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Rebooting the computer now...${NOCOLOR}"
    echo ""

    # Add a cron job to run the second script once after reboot
    (crontab -l 2>/dev/null; echo "@reboot $SCRIPT --rebooted=true") | crontab -
    sudo reboot
}


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
code_post_reboot() {

    # Remove the cron job to ensure the script runs only once
    crontab -l | grep -v "@reboot $SCRIPT --rebooted=true" | crontab -


    clear
    echo "================================================================================"
    echo -e "${YELLOW}Initializing the database${NOCOLOR}"
    echo ""

    INIT_DB_URL="http://localhost:5000/api/initializeDatabase/"
    echo -e "Calling: ${BLUE} $INIT_DB_URL ${NOCOLOR}"

    curl -s $INIT_DB_URL | jq '.'


    echo ""
    echo "================================================================================"
    echo "================================================================================"
    echo "================================================================================"
    echo ""
    echo -e "${GREEN}The installation is done.${NOCOLOR}"
    echo ""
}


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
clear

echo "Rebooted-flag is set to: $REBOOTED"

if [ $REBOOTED == "false" ]; then
    code_pre_reboot
else
    code_post_reboot
fi