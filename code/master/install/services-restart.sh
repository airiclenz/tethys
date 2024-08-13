
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