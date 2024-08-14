
# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")


echo "Clearing the logs..."

cd $SCRIPTPATH
./services-clearLogs.sh


sudo systemctl restart tethys-api.service
echo "Restarted tethys-api"

sudo systemctl restart tethys-core.service
echo "Restarted tethys-core"

sudo systemctl restart tethys-web.service
echo "Restarted tethys-web"

sudo systemctl restart tethys-watchdog.service
echo "Restarted tethys-watchdog"

sudo systemctl restart nginx
echo "Restarted nginx"

sudo systemctl restart redis-server
echo "Restarted redis-server"

sudo systemctl restart daphne.service
echo "Restarted daphne"