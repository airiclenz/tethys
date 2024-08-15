from datetime import datetime

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATETIME_FORMAT_NO_MILL = '%Y-%m-%dT%H:%M:%S'

# =============================================================================
# used for tracking which sensor sent data recently - for action handling
class SilentPhase:
    lastCalculationTime = datetime.min
    startTime = datetime.min
    endTime = datetime.min
    inPhase = False


LAST_DATA_UPDATE = datetime.min
SILENT_PHASE = SilentPhase()