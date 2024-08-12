#!/usr/bin/env python3

import sys

# =============================================================================
def updateTokenInFile(filename, tokenString, replacementString):
	
	# read the file into an array
	with open(filename, "r") as f:
		lines = [line.rstrip() for line in f]
		f.close()
		
	# Go through all the lines and search for correct line
	with open(filename, "w") as f:

		# go through all lines and look for the string {TETHYS-PATH}
		for line in lines:
			
			if  "{TETHYS-PATH}" in line:
				line = line.replace(tokenString, replacementString)
				f.write(line + "\n")
				
			else:

				f.write(line + "\n")

		f.close()




# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if len(sys.argv) != 4:
	print("Expecting three parameters: ('fileName', 'token', 'replacement')! --> Leaving...")
	sys.exit()


fileName = sys.argv[1]
tokenString = sys.argv[2]
replacementString = sys.argv[3] 

updateTokenInFile(fileName, tokenString, replacementString)




