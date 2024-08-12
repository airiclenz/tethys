from datetime import datetime


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATETIME_FORMAT_NO_MILL = '%Y-%m-%dT%H:%M:%S'

BASE_API_URL = 'http://localhost:5001/api/'

class BG_COLORS:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# =============================================================================
# used for tracking which sensor sent data recently - for action handling
class SilentPhase:
    lastCalculationTime = datetime.min
    startTime = datetime.min
    endTime = datetime.min
    inPhase = False


LAST_DATA_UPDATE = datetime.min
SILENT_PHASE = SilentPhase()