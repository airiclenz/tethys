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