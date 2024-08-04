

print("//////////////////////////////////////////////////////")
print("Running Build Number Script now...")

filename_version = "include/wpw_Version.h"
isRelease = False

# read the file into an array
with open(filename_version, "r") as f:
	lines = [line.rstrip() for line in f]

	f.close()

print("Opened the file '" + filename_version + "'.")


with open(filename_version, "w") as f:

	# go through all lines until the buildnumber is found
	for line in lines:
		
		if "#define" in line and "RELEASE" in line and "//" not in line:
			
			print("RELEASE was defined --> No build number increase")
			isRelease = True
			
				
		if "BUILDNUMBER" in line and not isRelease:

			print("Found the line with the BUILDNUMBER")

			# search for a space from the end
			parts = line.rsplit("\t", 1)

			print("Existing build number = " + parts[1])

			# increment the buildnumber by one
			buildNumber = int(parts[1])
			buildNumber = buildNumber + 1

			print("Build number is now   = " + str(buildNumber))

			# re-form the line with the new build number
			line = parts[0] + "\t" + str(buildNumber)

			f.write(line + "\n")

		else:

			f.write(line + "\n")

	f.close()

print("//////////////////////////////////////////////////////")