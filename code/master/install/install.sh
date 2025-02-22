#!/bin/bash
set -e  # Exit if any command fails

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

    sudo apt update -y && sudo apt full-upgrade -y
    sudo apt install -y \
        python3-venv python3-full python3-dev \
        libopenblas-dev nginx redis-server jq

    if [ $DEBUG == "true" ]; then
        # used for installing npm - the typescript compiler
        sudo apt install npm -y
        sudo npm install -g typescript
    fi


    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Setting up the python environment${NOCOLOR}"
    echo ""

    if [ ! -d "$VENV_NAME/bin" ]; then
        echo $VENV_NAME " environment was not found. Creating..."
        python3 -m venv "$VENV_NAME"
    else
        echo "Virtual environment exists."
    fi

    source $VENV_NAME/bin/activate
    echo "The virtual environment" $VENV_NAME "was activated."

    echo "Updating the pip installer."
    python3 -m pip install --upgrade pip

    echo "Installing needed packages now..."
    pip install -r ./install/python-requirements.txt


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

    # cd $ROOTPATH/install
    # enable SPI
    #sudo python3 enableSpi.py
    
    # Enable SPI by adding the necessary line to /boot/config.txt
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    # enable the redis-server
    sudo systemctl enable --now redis-server

    echo ""
    echo "================================================================================"
    echo -e "${YELLOW}Calling sub-script for installation of the services...${NOCOLOR}"
    echo ""

    cd $SCRIPTPATH

    # run the service install script
    ./installServices.sh --debug=$DEBUG

    echo ""
    echo "================================================================================"
    echo ""
    echo -e "${NOCOLOR}The computer needs to be re-booted. ${YELLOW}Do you want to continue?${NOCOLOR}"
    echo ""
    echo -e "[ ${GREEN}yes${NOCOLOR} / ${RED}no${NOCOLOR} ]"
    echo ""
    
    read answer

    if [ "$answer" != "${answer#[Yy]}" ] ;then
        echo "Proceeding..."
        
        # Configure rc.local to run the script with the given parameter after reboot
        sudo bash -c 'echo "$SCRIPT --rebooted=true" >> /etc/rc.local'
        sudo reboot
    else
        echo "After the computer was rebooted, run this script again with this command:"
        echo -e "${BLUE}./install.sh --rebooted=true ${NOCOLOR}"
    fi

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

    RETRIES=5
    for i in $(seq 1 $RETRIES); do
        if curl -s --connect-timeout 5 "$INIT_DB_URL" | jq '.'; then
            echo "Database initialized successfully!"
            break
        else
            echo "Retrying database initialization... ($i/$RETRIES)"
            sleep 5
        fi
    done


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