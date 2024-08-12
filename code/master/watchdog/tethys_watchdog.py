#!/usr/bin/env python3

import schedule
import time
import os


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# This Service checks the other services of tethys. The core service is
# restarted every 24h.

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


# /////////////////////////////////////////////////////////////////////////////
def restartServices():
    os.system("systemctl restart tethys-api.service")
    os.system("systemctl restart tethys-core.service")
    
    print("Services were restarted.")

    os.system("journalctl --vacuum-time=1d")

    print("Services-journals were truncated.")


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
schedule.every().day.at("01:00").do(restartServices)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:
    schedule.run_pending()

    # the scheduler takes care of everything so we can just sleep...
    # sleep for one minute
    time.sleep(60)