#!/usr/bin/env python3

import string
import random
import configparser
import os


CONFIG_FILE = 'config.ini'


# =============================================================================
def generatePassword(
	length = 30):

	letters = string.ascii_letters
	numbers = string.digits  
	punctuation = string.punctuation  

	punctuation = punctuation.replace("%", "")
		

	# create alphanumerical from string constants
	printable = f'{letters}{numbers}{punctuation}'

	# convert printable from string to list and shuffle
	printable = list(printable)
	random.shuffle(printable)

	# generate random password and convert to string
	random_password = random.choices(printable, k=length)
	random_password = ''.join(random_password)
	return random_password


scriptPath = os.path.dirname(os.path.abspath(__file__))
# create parser and read ini configuration file
config = configparser.ConfigParser()
filePath = scriptPath + "/../src/" + CONFIG_FILE
config.read(filePath)

password = generatePassword()

config["misc"]["secret"] = password
			
with open(filePath, 'w') as configFile:
	config.write(configFile)

print ("A new secret was created.")