#!/bin/bash

# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")
LENGTH=${#SCRIPTPATH}
ENDPOS=`expr $LENGTH - 8`
# The root directory of the code for the raspberry pi - within the git that is './tethys/code/master'
ROOTPATH=$(echo $SCRIPTPATH| cut -c$1-$ENDPOS)

VENV_NAME="env_tethys"


clear
echo "=====  STARTING the installation of TETHYS  ===================================="
echo ""
echo "Root path:  " $ROOTPATH
echo "Script path:" $SCRIPTPATH

cd $ROOTPATH

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   S Y S T E M   U P D A T E
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ""
echo "================================================================================"
echo "Running a system update / upgrade"

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


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   P Y T H O N - V E N V
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo ""
echo "================================================================================"
echo "Setting up the python environment"

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
echo "Handling django migrations now..."

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


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   S E R V I C E S
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

cd $ROOTPATH/install

echo ""
echo "================================================================================"
echo "Enabling SPI"

# enable SPI
sudo python3 enableSpi.py

echo ""
echo "================================================================================"
echo "Calling sub-script for installation of the services..."

# run the service install script
./installServices.sh

echo ""
echo "================================================================================"
echo "================================================================================"
echo "================================================================================"
echo "The installation is done."
echo ""