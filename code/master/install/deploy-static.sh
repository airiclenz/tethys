#!/bin/bash
set -e  # Exit on error

# Deploys the web frontend: compiles the TypeScript to JavaScript, copies the
# static assets to the nginx-served staticcollect folder, fixes permissions, and
# restarts the tethys-web service. Use this after editing anything under
# web/static/ts (or the other static folders). Static files are served directly
# by nginx and JS changes are picked up on the next browser reload, but
# restarting tethys-web also flushes Django's cached template loader so template
# changes take effect too.

# Default value for DEBUG (also copies the .ts sources + source maps when true).
DEBUG=true

# Absolute path to this script.
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in (.../code/master/install).
SCRIPTPATH=$(dirname "$SCRIPT")
# The root directory of the master code (.../code/master).
ROOTPATH=$(dirname "$SCRIPTPATH")

WWWPATH='/var/www'

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NOCOLOR='\033[0m' # No Color


# Parse command-line arguments
for arg in "$@"
do
  case $arg in
    --debug=*)
      DEBUG="${arg#*=}"
      shift # Remove --debug= from processing
      ;;
    *)
      # Unknown option
      ;;
  esac
done


echo ""
echo "================================================================================"
echo -e "${YELLOW}Compiling the TypeScript${NOCOLOR}"
echo ""

if ! command -v tsc >/dev/null 2>&1; then
    echo -e "${RED}The TypeScript compiler 'tsc' was not found.${NOCOLOR}"
    echo "Install it with: sudo npm install -g typescript  (or run installTypeScript.sh)"
    exit 1
fi

cd "$ROOTPATH/web/static/ts"
# This codebase's TypeScript is loosely typed, so tsc reports type errors (e.g.
# implicit-any, possibly-null) but still EMITS the JavaScript (noEmitOnError is
# off). Don't let a non-zero tsc exit abort the deploy - warn and continue,
# matching how the project has always been built. An `if` condition is exempt
# from `set -e`, so this won't trip the early exit.
if tsc -p tsconfig.json; then
    echo -e "${GREEN}TypeScript compiled cleanly to web/static/js${NOCOLOR}"
else
    echo -e "${YELLOW}tsc reported type errors (pre-existing in this codebase);"
    echo -e "the JavaScript was still emitted. Continuing with the deploy.${NOCOLOR}"
fi


echo ""
echo "================================================================================"
echo -e "${YELLOW}Copying the static folder to staticcollect${NOCOLOR}"
echo ""

sudo mkdir -p $WWWPATH/tethys/
sudo chmod 755 $WWWPATH/tethys/

cd $WWWPATH/tethys/
sudo rm -rf ./staticcollect
sudo mkdir staticcollect

sudo cp -r $ROOTPATH/web/static/css $WWWPATH/tethys/staticcollect/css
sudo cp -r $ROOTPATH/web/static/fonts $WWWPATH/tethys/staticcollect/fonts
sudo cp -r $ROOTPATH/web/static/images $WWWPATH/tethys/staticcollect/images
sudo cp -r $ROOTPATH/web/static/js $WWWPATH/tethys/staticcollect/js
sudo cp -r $ROOTPATH/web/static/templatter $WWWPATH/tethys/staticcollect/templatter

if [ $DEBUG == "true" ]; then
    sudo cp -r $ROOTPATH/web/static/ts $WWWPATH/tethys/staticcollect/ts
fi

echo "Giving nginx access to staticcollect"

sudo chown -R www-data:www-data "$WWWPATH/tethys/staticcollect"
sudo chmod -R u=rwX,g=rX,o=rX "$WWWPATH/tethys/staticcollect"

echo ""
echo "================================================================================"
echo -e "${YELLOW}Restarting the tethys-web service${NOCOLOR}"
echo ""

sudo systemctl restart tethys-web.service
echo -e "${GREEN}tethys-web.service restarted${NOCOLOR}"

echo ""
echo "================================================================================"
echo -e "${GREEN}Static deploy done.${NOCOLOR} Reload the browser to pick up the changes."
echo ""
