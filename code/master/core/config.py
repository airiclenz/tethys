from datetime import datetime

from hardware import CHANNEL_COUNT


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATETIME_FORMAT_NO_MILL = '%Y-%m-%dT%H:%M:%S'

BASE_API_URL = 'http://localhost:5000/api/'

TIME_ZONE = 'Europe/Stockholm'


# =============================================================================
# Shared mailbox between radio (producer) and actionEngine (consumer): which
# channels have sent fresh sensor data and may need a watering action.
# `channelFlags` is deliberately a class-level attribute so both sides see the
# same list regardless of how FlagHandler is referenced. Its length tracks the
# real channel count (was hardcoded to 6 while the hardware has 5).
class FlagHandler:
    channelFlags = [False] * CHANNEL_COUNT

