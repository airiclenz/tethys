
from zoneinfo import ZoneInfo
from datetime import datetime

from .models import Schedule
from .silentphase import evaluate_silent_phase
from .globals import *



# =============================================================================
def getTimeAsLocalDateTime(timestamp, zoneInfo):

    if timestamp == datetime.min:
        return timestamp

    zoneInfo
    return timestamp.astimezone(zoneInfo)



# =============================================================================
def refreshSilentPhaseStatus(timeZoneIdentifier, forceRecaclulation=False):

    """
    This re-evaluates if we have a silent-schedule that is active right now.

    All time comparisons happen in the caller-supplied timezone so the window
    matches the user's declared local quiet hours. (Previously the math mixed a
    naive UTC-derived window with the server's naive local clock, offsetting the
    window by the server's UTC<->local difference.)
    """

    timeZoneInfo = ZoneInfo(timeZoneIdentifier.replace('-', '/'))
    now = datetime.now(timeZoneInfo)

    isDataUpdate = False
    isEnteringSilentPhase = False
    isLeavingSilentPhase = False

    isInit = SILENT_PHASE.lastCalculationTime == datetime.min

    if isInit is False:
        # getLastDataUpdate() is a naive server-local timestamp (or the
        # datetime.min sentinel until the first data-mutating request). Only
        # compare once it has actually been set, and localize it to an aware
        # datetime so it is comparable to the timezone-aware lastCalculationTime.
        lastDataUpdate = getLastDataUpdate()
        isDataUpdate = (
            lastDataUpdate != datetime.min
            and SILENT_PHASE.lastCalculationTime < lastDataUpdate.astimezone()
        )

        isEnteringSilentPhase = (
            SILENT_PHASE.startTime < now and SILENT_PHASE.inPhase is False
        )

        isLeavingSilentPhase = (
            SILENT_PHASE.endTime < now and SILENT_PHASE.inPhase
        )

    # --------------------------------
    # only calculate if we need to
    if (
        forceRecaclulation
        or isDataUpdate
        or isInit
        or isEnteringSilentPhase
        or isLeavingSilentPhase
    ):
        updateReason = ""

        if isDataUpdate:
            updateReason = "Data Update"

        if isInit:
            if updateReason != "":
                updateReason += " | "
            updateReason += "Init"

        if forceRecaclulation:
            if updateReason != "":
                updateReason += " | "
            updateReason += "Force"

        if isEnteringSilentPhase:
            if updateReason != "":
                updateReason += " | "
            updateReason += "Entering Silent Phase"

        if isLeavingSilentPhase:
            if updateReason != "":
                updateReason += " | "
            updateReason += "Leaving Silent Phase"

        print("=============================================")
        print("Silent phase status is re-evaluated now...")
        print(f"[ {updateReason} ]")
        print(".............................................")

        print(f"last calculation:  {getTimeAsLocalDateTime(SILENT_PHASE.lastCalculationTime, timeZoneInfo)}")
        print(f"last data update:  {getLastDataUpdate()}")
        print(f"silence start:     {SILENT_PHASE.startTime}")
        print(f"silence end:       {SILENT_PHASE.endTime}")
        print(f"old state:         {SILENT_PHASE.inPhase}")

        SILENT_PHASE.lastCalculationTime = now

        # Load the Offline Times to check if we are supposed to wait
        # (Don't forget to add a 5min block around the restart time)
        silent_schedules = loadSilentSchedules()

        if silent_schedules == None:
            SILENT_PHASE.inPhase = False
            return False

        inPhase, startTime, endTime = evaluate_silent_phase(silent_schedules, now)

        SILENT_PHASE.inPhase = inPhase
        SILENT_PHASE.startTime = startTime
        SILENT_PHASE.endTime = endTime

        print(".............................................")
        print(f"new last calc:     {getTimeAsLocalDateTime(SILENT_PHASE.lastCalculationTime, timeZoneInfo)}")
        print(f"new state:         {SILENT_PHASE.inPhase}")
        print(f"new silence start: {SILENT_PHASE.startTime}")
        print(f"new silence end:   {SILENT_PHASE.endTime}", flush=True)

        return inPhase

    else:
        return SILENT_PHASE.inPhase


# =============================================================================
def loadSilentSchedules():

    """
    Retrieves all enabled schedules of type silent.
    """

    return Schedule.objects.filter(enabled=True, scheduleType__name="silent")
