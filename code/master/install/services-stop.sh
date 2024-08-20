
# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")


show_progress() {
  local pid=$1
  local delay=0.5

  while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do

    #printf " "
    sleep $delay
    #printf "\b"
    
    printf " "
    sleep $delay
    printf "\b"
    
  done
}



echo "Stopping the services"

printf " > Stopping tethys-api.service...      "
sudo systemctl stop tethys-api.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped tethys-api.service         OK\n"


printf " > Stopping tethys-core.service...     "
sudo systemctl stop tethys-core.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped tethys-core.service        OK\n"


printf " > Stopping tethys-web.service...      "
sudo systemctl stop tethys-web.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped tethys-web.service         OK\n"


printf " > Stopping tethys-watchdog.service... "
sudo systemctl stop tethys-watchdog.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped tethys-watchdog.service    OK\n"


printf " > Stopping nginx...                   "
sudo systemctl stop nginx & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped nginx                      OK\n"


printf " > Stopping redis-server...            "
sudo systemctl stop redis-server & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped redis-server               OK\n"


printf " > Stopping daphne.service...          "
sudo systemctl stop daphne.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Stoppped daphne.service             OK\n"

