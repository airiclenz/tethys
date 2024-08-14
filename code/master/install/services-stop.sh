
# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")



sudo systemctl stop tethys-api.service
echo "Stopped tethys-api"

sudo systemctl stop tethys-core.service
echo "Stopped tethys-core"

sudo systemctl stop tethys-web.service
echo "Stopped tethys-web"

sudo systemctl stop tethys-watchdog.service
echo "Stopped tethys-watchdog"

sudo systemctl stop nginx
echo "Stopped nginx"

sudo systemctl stop redis-server
echo "Stopped redis-server"

sudo systemctl stop daphne.service
echo "Stopped daphne"