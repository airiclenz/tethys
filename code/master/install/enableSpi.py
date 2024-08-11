#!/usr/bin/env python3


filename = "/boot/config.txt"
updated = False


# read the file into an array
with open(filename, "r") as f:
	lines = [line.rstrip() for line in f]

	f.close()

	
# Go through all the lines and search for the SPI setting
with open(filename, "w") as f:

	# go through all lines until the SPI-setting is found
	for line in lines:
		
		if  "dtparam=spi=on" in line and \
			"#" in line:
			
			line = "dtparam=spi=on"
			f.write(line + "\n")
			updated = True

		else:

			f.write(line + "\n")

	f.close()
	

# do some final logging
if updated == True:
	
	print("SPI was enabled")
	
else:
	
	print("SPI is already enabled on this Raspberry Pi")
	