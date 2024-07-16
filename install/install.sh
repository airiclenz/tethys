#!/bin/bash

# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPT_PATH=$(dirname "$SCRIPT")
VENV_NAME="env"

cd $SCRIPT_PATH
cd ..
echo "Current Directory: $(pwd)"

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   S Y S T E M   U P D A T E
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

sudo apt update
sudo apt full-upgrade

# sudo apt install libssl-dev libncurses5-dev libsqlite3-dev libreadline-dev libtk8.6 libgdm-dev libdb4o-cil-dev libpcap-dev -y
# sudo apt-get install openssl

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#   P Y T H O N - V E N V
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

PYTHON_PACKAGES = "django channels channels-redis channels_redis daphne requests gpiozero djangorestframework django-rest-swagger"

if [ ! -d $VENV_NAME ]; then
    echo $VENV_NAME "does not exist -> creating it now..."
    python -m venv $VENV_NAME
fi

source $VENV_NAME/bin/activate
echo "the new virtual environment" $VENV_NAME "was activated."
echo "installing needed packages now..."
pip install django $PYTHON_PACKAGES


