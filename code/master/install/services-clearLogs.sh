
# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")

sudo journalctl --rotate

sudo journalctl --vacuum-time=1s -u tethys_api.service
sudo journalctl --vacuum-time=1s -u tethys_core.service
sudo journalctl --vacuum-time=1s -u tethys_web.service
sudo journalctl --vacuum-time=1s -u tethys_watchdog.service
sudo journalctl --vacuum-time=1s -u daphne.service
sudo journalctl --vacuum-time=1s -u redis-server

echo ""
echo "Journals were cleaned up..."



###############################################################################
# checking the error log:
# sudo journalctl -u tethys-api.service
# sudo journalctl -u tethys-core.service
# sudo journalctl -u tethys-web.service
# sudo journalctl -u tethys-watchdog.service

# sudo journalctl -u daphne.service
# sudo journalctl -u redis-server

# sudo journalctl -u nginx
# systemctl status nginx.service
# journalctl -xeu nginx.service
# sudo nano /var/log/nginx/error.log