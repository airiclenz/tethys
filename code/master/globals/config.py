from packaging.version import Version

version = Version("3.0.0")

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATETIME_FORMAT_NO_MILL = '%Y-%m-%dT%H:%M:%S'

# Single source of truth for the deployment timezone. The Django API stores and
# interprets schedule times in this zone, and the core localizes the silent-phase
# window against the same zone.
TIME_ZONE = 'Europe/Stockholm'
