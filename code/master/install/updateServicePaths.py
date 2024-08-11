#!/usr/bin/env python3

import sys

# =============================================================================
def updatePath(filename, newPath):
	
	# read the file into an array
	with open(filename, "r") as f:
		lines = [line.rstrip() for line in f]
		f.close()
		
	# Go through all the lines and search for correct line
	with open(filename, "w") as f:

		# go through all lines and look for the string {TETHYS-PATH}
		for line in lines:
			
			if  "{TETHYS-PATH}" in line:
				line = line.replace('{TETHYS-PATH}', newPath)
				f.write(line + "\n")
				
			else:

				f.write(line + "\n")

		f.close()




# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if len(sys.argv) != 3:
	print("Expecting two parameters: ('fileName', 'newTethysPath')! --> Leaving...")
	sys.exit()


updatePath(sys.argv[1], sys.argv[2])
#updatePath("./services-local/tethys-core.service", sys.argv[1])
#updatePath("./services-local/tethys-watchdog.service", sys.argv[1])
#updatePath("./services-local/tethys-web.service", sys.argv[1], "tethys_web.py")



