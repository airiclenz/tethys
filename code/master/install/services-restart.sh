
# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")

CLEARLOGS=false


# Parse command-line arguments
for arg in "$@"
do
  case $arg in
    --clearlogs=*)
      CLEARLOGS="${arg#*=}"
      shift # Remove --debug= from processing
      ;;
    *)
      # Unknown option
      ;;
  esac
done

echo ""

if [ $CLEARLOGS == "true" ]; then

    echo "Clearing the logs..."
    cd $SCRIPTPATH
    ./services-clearLogs.sh
    echo ""

fi


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

# make the curesor invisible
# tput civis

echo "Starting / Re-starting the services"

printf " > Restarting tethys-api.service       "
sudo systemctl restart tethys-api.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting tethys-api.service       OK\n"

printf " > Restarting tethys-core.service      "
sudo systemctl restart tethys-core.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting tethys-core.service      OK\n"

printf " > Restarting tethys-web.service       "
sudo systemctl restart tethys-web.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting tethys-web.service       OK\n"

printf " > Restarting tethys-watchdog.service  "
sudo systemctl restart tethys-watchdog.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting tethys-watchdog.service  OK\n"

printf " > Restarting nginx                    "
sudo systemctl restart nginx & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting nginx                    OK\n"

printf " > Restarting redis-server             "
sudo systemctl restart redis-server & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting redis-server             OK\n"

printf " > Restarting daphne.service           "
sudo systemctl restart daphne.service & pid=$!
show_progress $pid
wait $pid
printf "\r > Restarting daphne.service           OK\n"

# make the curesor visible
# tput cnorm