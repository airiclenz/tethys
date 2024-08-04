#!/bin/bash

GREEN="\\e[92m"
NO_COLOR="\\e[39m"

echo -e "> Compiling type-script to jScript now..."
tsc --build --verbose
echo -e "> ${GREEN}Compiling done.${NO_COLOR}"