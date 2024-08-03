#!/bin/bash

# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPT_PATH=$(dirname "$SCRIPT")
VENV_NAME="env_tethys"

cd $SCRIPT_PATH
cd ..
echo :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo "Current Directory: $(pwd)"



# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   S Y S T E M   U P D A T E
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

sudo apt update -y
sudo apt full-upgrade -y

# needed for numpy on the Raspberry Pi
sudo apt install libopenblas-dev -y
# needed for the nRF24 module
sudo apt install pigpio python-pigpio python3-pigpio



# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   P Y T H O N - V E N V
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

if [ ! -d $VENV_NAME ]; then
    echo :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    echo $VENV_NAME "does not exist -> creating it now..."
    python3 -m venv $VENV_NAME
fi

source $VENV_NAME/bin/activate
echo :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo "the new virtual environment" $VENV_NAME "was activated."

echo :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo "updating the pip installer."
python3 -m pip install --upgrade pip

echo :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo "installing needed packages now..."
pip install -r ./install/python-requirements.txt



# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   M I G R A T I O N S
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

echo :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo "handling django migrations now..."

cd api
python manage.py makemigrations tethys_api
python manage.py migrate
cd ..

cd web
python manage.py makemigrations tethys_web
python manage.py migrate
cd ..