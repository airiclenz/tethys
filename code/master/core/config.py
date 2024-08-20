from datetime import datetime


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATETIME_FORMAT_NO_MILL = '%Y-%m-%dT%H:%M:%S'

BASE_API_URL = 'http://localhost:5000/api/'

TIME_ZONE = 'Europe/Stockholm'


# =============================================================================
# used for tracking which sensor sent data recently - for action handling
class FlagHandler:
    channelFlags = [False, False, False, False, False]

FLAG_HANDLER = FlagHandler()

