from datetime import datetime


# =============================================================================
# used for tracking which sensor sent data recently - for action handling
class SilentPhase:
    lastCalculationTime = datetime.min
    startTime = datetime.min
    endTime = datetime.min
    inPhase = False


LAST_DATA_UPDATE = datetime.min
SILENT_PHASE = SilentPhase()


# =============================================================================
# Read/write LAST_DATA_UPDATE through these helpers, never via `from .globals
# import LAST_DATA_UPDATE`. A plain `from import` copies the *binding* into the
# caller's module, so rebinding it there (the old `views.setLastDataUpdateNow`)
# updated only the caller's copy and never this canonical value -- so the
# silent-phase recalc trigger in common.py, which reads it here, never fired.
# A function body always resolves the global in *this* module at call time, so
# every caller shares one value.
def setLastDataUpdate():
    global LAST_DATA_UPDATE
    LAST_DATA_UPDATE = datetime.now()


def getLastDataUpdate():
    return LAST_DATA_UPDATE