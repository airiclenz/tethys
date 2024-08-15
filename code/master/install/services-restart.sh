
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

printf "Restarting tethys-api.service..."
sudo systemctl restart tethys-api.service
printf "\rRestarting tethys-api.service       Done\n"

printf "Restarting tethys-core.service..."
sudo systemctl restart tethys-core.service
printf "\rRestarting tethys-core.service      Done\n"

printf "Restarting tethys-web.service..."
sudo systemctl restart tethys-web.service
printf "\rRestarting tethys-web.service       Done\n"

printf "Restarting tethys-watchdog.service..."
sudo systemctl restart tethys-watchdog.service
printf "\rRestarting tethys-watchdog.service  Done\n"

printf "Restarting nginx..."
sudo systemctl restart nginx
printf "\rRestarting nginx                    Done\n"

printf "Restarting redis-server..."
sudo systemctl restart redis-server
printf "\rRestarting redis-server             Done\n"

printf "Restarting daphne.service..."
sudo systemctl restart daphne.service
printf "\rRestarting daphne.service           Done\n"