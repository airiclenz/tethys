
from zoneinfo import ZoneInfo
from datetime import datetime, date, timedelta

from .models import Schedule
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
    """

    # datetime.replace(tzinfo=timezone.utc)
    # datetime.now(timezone.utc)

    timeZoneInfo = ZoneInfo(timeZoneIdentifier.replace('-', '/'))
    isDataUpdate = False
    isEnteringSilentPhase = False
    isLeavingSilentPhase = False

    isInit = SILENT_PHASE.lastCalculationTime == datetime.min

    if isInit is False:
        isDataUpdate = SILENT_PHASE.lastCalculationTime < LAST_DATA_UPDATE

        isEnteringSilentPhase = (
            SILENT_PHASE.startTime < datetime.now() and SILENT_PHASE.inPhase is False
        )

        isLeavingSilentPhase = (
            SILENT_PHASE.endTime < datetime.now() and SILENT_PHASE.inPhase
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
        print(f"last data update:  {LAST_DATA_UPDATE}")
        print(f"silence start:     {SILENT_PHASE.startTime}")
        print(f"silence end:       {SILENT_PHASE.endTime}")
        print(f"old state:         {SILENT_PHASE.inPhase}")

        SILENT_PHASE.lastCalculationTime = datetime.now()

        # Load the Offline Times to check if we are supposed to wait
        # (Don't forget to add a 5min block around the restart time)
        silent_schedules = loadSilentSchedules()

        if silent_schedules == None:
            SILENT_PHASE.inPhase = False
            return False

        else:
            start_time = None
            end_time = None
            start_time_next = datetime.max.replace()
            end_time_next = datetime.max
            today = date.today()
            is_today = False
            yesterday = date.today() - timedelta(days=1)

            # loop through the silent schedules
            for schedule in silent_schedules:
                # only continue if the weekday is the same as today or
                # yesterday (for long)
                if (today.strftime("%A") == schedule.weekday) or (
                    yesterday.strftime("%A") == schedule.weekday
                ):
                    start_time = schedule.startTime
                    
                    if today.strftime("%A") == schedule.weekday:
                        # add the date component (from today) to the start time
                        start_time = datetime(
                            today.year,
                            today.month,
                            today.day,
                            start_time.hour,
                            start_time.minute,
                        )

                        is_today = True

                    else:
                        # add the date component (from today) to the start time
                        start_time = datetime(
                            yesterday.year,
                            yesterday.month,
                            yesterday.day,
                            start_time.hour,
                            start_time.minute,
                        )

                        is_today = False

                    # add the duration in minutes to the start time to get the end time
                    end_time = start_time + timedelta(minutes=schedule.durationMinutes)
                    end_time = end_time
                    
                    # if now is between the start- and the end-time, then we are
                    # in a silent phase
                    if start_time < datetime.now() < end_time:
                        SILENT_PHASE.inPhase = True
                        SILENT_PHASE.startTime = start_time
                        SILENT_PHASE.endTime = end_time

                        print(".............................................")
                        print(f"new last calc:     {getTimeAsLocalDateTime(SILENT_PHASE.lastCalculationTime, timeZoneInfo)}")
                        print(f"new state:         {SILENT_PHASE.inPhase}")
                        print(f"new silence start: {SILENT_PHASE.startTime}")
                        print(f"new silence end:   {SILENT_PHASE.endTime}", flush=True)

                        return True

                    # if we are not in a silent phase withthe current schedule,
                    # see if it could be the upcoming schedule (after now but before
                    # the previous nex-schedule saved already):
                    elif is_today:
                        if (start_time > datetime.now()) and (start_time < start_time_next):
                            start_time_next = start_time
                            end_time_next = end_time

            # loop schedules

        SILENT_PHASE.inPhase = False
        SILENT_PHASE.startTime = start_time_next
        SILENT_PHASE.endTime = end_time_next

        print(".............................................")
        print(f"new last calc:     {SILENT_PHASE.lastCalculationTime}")
        print(f"new state:         {SILENT_PHASE.inPhase}")
        print(f"new silence start: {SILENT_PHASE.startTime}")
        print(f"new silence end:   {SILENT_PHASE.endTime}", flush=True)

        return False

    else:
        return SILENT_PHASE.inPhase
    

# =============================================================================
def loadSilentSchedules():

    """
    Retrieves all schedules of type silent.
    """

    return Schedule.objects.filter(enabled=True)