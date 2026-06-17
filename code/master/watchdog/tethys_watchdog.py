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
    # Absolute binary paths are required: the systemd unit pins PATH to the venv
    # bin (Environment=PATH=.../env_tethys/bin), so os.system()'s /bin/sh cannot
    # resolve bare "systemctl"/"journalctl" — it logged "not found" and this
    # function still printed success. Same fix as the /api/reboot/ endpoint.
    api = os.system("/usr/bin/systemctl restart tethys-api.service")
    core = os.system("/usr/bin/systemctl restart tethys-core.service")

    if api == 0 and core == 0:
        print("Services were restarted.")
    else:
        print(f"Service restart FAILED (api={api}, core={core}).")

    vac = os.system("/usr/bin/journalctl --vacuum-time=1d")

    print("Services-journals were truncated." if vac == 0
          else f"Journal vacuum FAILED ({vac}).")


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
schedule.every().day.at("01:00").do(restartServices)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# keep on swimming, keep on swimming, keep on swimming swimming swimming...
while 1:
    schedule.run_pending()

    # the scheduler takes care of everything so we can just sleep...
    # sleep for one minute
    time.sleep(60)