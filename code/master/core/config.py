import os
import sys
from datetime import datetime

from hardware import CHANNEL_COUNT

# Make the shared `globals` package (code/master/globals) importable. This module
# is imported very early (the service runs with WorkingDirectory=core/, so only
# core/ is on the path), before the entry point appends the master dir.
_master_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _master_dir not in sys.path:
    sys.path.append(_master_dir)

from globals.config import TIME_ZONE


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATETIME_FORMAT_NO_MILL = '%Y-%m-%dT%H:%M:%S'

BASE_API_URL = 'http://localhost:5000/api/'


# =============================================================================
# Shared mailbox between radio (producer) and actionEngine (consumer): which
# channels have sent fresh sensor data and may need a watering action.
# `channelFlags` is deliberately a class-level attribute so both sides see the
# same list regardless of how FlagHandler is referenced. Its length tracks the
# real channel count (was hardcoded to 6 while the hardware has 5).
class FlagHandler:
    channelFlags = [False] * CHANNEL_COUNT

