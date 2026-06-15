from django.db import models
import logging


# Number of sensor/pump channels the system supports. Bounded by the hardware:
# the master exposes 5 pump GPIOs and the nRF24L01 has 6 pipes, one of which
# (pipe 0) is reserved for the writing/ACK address - leaving 5 sensor channels.
# Mirrors core.hardware.CHANNEL_COUNT (kept as a literal here because the api
# app does not import from core).
CHANNEL_COUNT = 5


WEEKDAYS = (
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday")
)


# /////////////////////////////////////////////////////////////////////////////
class ActionType(models.Model):
    '''The available action types.'''
    name = models.CharField(max_length=20, primary_key=True, unique=True)

    def __str__(self) -> str:
        return self.name

# /////////////////////////////////////////////////////////////////////////////
class ChannelType(models.Model):
    '''The available channel types'''
    name = models.CharField(max_length=20, primary_key=True, unique=True)

    def __str__(self) -> str:
        return self.name

# /////////////////////////////////////////////////////////////////////////////
class ScheduleType(models.Model):
    '''The available schedule-types'''
    name = models.CharField(max_length=20, primary_key=True, unique=True)

    def __str__(self) -> str:
        return self.name

# /////////////////////////////////////////////////////////////////////////////
class TransmissionPowerLevel(models.Model):
    '''The available transmission-power-levels'''
    name = models.CharField(max_length=20, primary_key=True, unique=True)
    value = models.IntegerField(unique = True);

    def __str__(self) -> str:
            return self.name



# /////////////////////////////////////////////////////////////////////////////
class Channel(models.Model):
    '''All existing channels'''
    number = models.IntegerField(primary_key=True, unique=True)
    enabled = models.BooleanField(default=False)
    nickName = models.CharField(max_length=100, blank=True, default="New Channel")
    channelType = models.ForeignKey(ChannelType, on_delete=models.DO_NOTHING)
    actionTriggerPercent = models.IntegerField()
    pumpDurationSeconds = models.IntegerField()
    sensorMeasureFrequencyMinutes = models.IntegerField()
    sensorTriggerCalibration = models.BooleanField(default=False)
    sensorTransmissionPowerLevel = models.ForeignKey(TransmissionPowerLevel, on_delete=models.DO_NOTHING)
    # Latest firmware version (VERSION.SUBVERSION.BUILDNUMBER) the sensor
    # reported on its last boot. Written by the master on the boot-time GETCONFIG
    # handshake; blank until a sensor has booted at least once.
    sensorFirmwareVersion = models.CharField(max_length=20, blank=True, default="")

    def __str__(self) -> str:
        return str(self.number) + ' - ' + self.nickName

# /////////////////////////////////////////////////////////////////////////////
class SensorData(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    batteryVoltage = models.FloatField()
    moisturePercent = models.SmallIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.channel.number) + ' - ' + self.timestamp

# /////////////////////////////////////////////////////////////////////////////
class ActionLog(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    actionType = models.ForeignKey(ActionType, on_delete=models.DO_NOTHING)
    # NOT auto_now_add: that stamped the row-insert time (which happens when the
    # pump *finishes*) instead of the real start the core supplies, so the saved
    # span was the UTC offset, not the pump duration. Store the posted start.
    startTime = models.DateTimeField()
    endTime = models.DateTimeField()

    def __str__(self) -> str:
        return str(self.channel.number) + ' - ' + self.actionType.name


# /////////////////////////////////////////////////////////////////////////////
class Schedule(models.Model):
    enabled = models.BooleanField(default=True)
    weekday = models.CharField(max_length=20, choices=WEEKDAYS)
    scheduleType = models.ForeignKey(ScheduleType, on_delete=models.DO_NOTHING)
    startTime = models.DateTimeField()
    durationMinutes = models.SmallIntegerField()

    def __str__(self) -> str:
        return self.weekday + ' - ' + self.scheduleType.name


# /////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////
class ModelHelper():



    # /////////////////////////////////////////////////////////////////////////////
    def initializeDatabase():
        
        logger = logging.getLogger(__name__)
        actionLog = []
        logger.debug( "Log test")


        # :::::::::::::::::::::
        try:
            channelTypePump = ChannelType.objects.get(pk = "pump")
            actionLog.append("Existing channel-type 'pump' was found.")
        except:
            channelTypePump = ChannelType(name = "pump")
            channelTypePump.save()
            actionLog.append("New channel-type 'pump' was created.")

        try:
            channelTypeValve = ChannelType.objects.get(pk = "valve")
            actionLog.append("Existing channel-type 'valve' was found.")
        except:
            channelTypeValve = ChannelType(name = "valve")
            channelTypeValve.save()
            actionLog.append("New channel-type 'valve' was created.")

        # :::::::::::::::::::::
        try:
            actionTypePump = ActionType.objects.get(name = "pump")
            actionLog.append("Existing action-type 'pump' was found.")
        except:
            actionTypePump = ActionType(name = "pump")
            actionTypePump.save()
            actionLog.append("New action-type 'pump' was created.")


        # :::::::::::::::::::::
        try:
            scheduleTypeSilent = ScheduleType.objects.get(pk = "silent")
            actionLog.append("Existing schedule-type 'silent' was found.")
        except:
            scheduleTypeSilent = ScheduleType(name = "silent")
            scheduleTypeSilent.save()
            actionLog.append("New schedule-type 'silent' was created.")
            
        # :::::::::::::::::::::
        try:
            transmissionPowerLevelMin = TransmissionPowerLevel.objects.get(pk = "min")
            actionLog.append("Existing transmission-power-level 'min' was found.")
        except:
            transmissionPowerLevelMin = TransmissionPowerLevel(name = "min", value = 0)
            transmissionPowerLevelMin.save()
            actionLog.append("New transmission-power-level 'min' was created.")

        try:
            transmissionPowerLevelLow = TransmissionPowerLevel.objects.get(pk = "low")
            actionLog.append("Existing transmission-power-level 'low' was found.")
        except:
            transmissionPowerLevelLow = TransmissionPowerLevel(name = "low", value = 1)
            transmissionPowerLevelLow.save()
            actionLog.append("New transmission-power-level 'low' was created.")

        try:
            transmissionPowerLevelHigh = TransmissionPowerLevel.objects.get(pk = "high")
            actionLog.append("Existing transmission-power-level 'high' was found.")
        except:
            transmissionPowerLevelHigh = TransmissionPowerLevel(name = "high", value = 2)
            transmissionPowerLevelHigh.save()
            actionLog.append("New transmission-power-level 'high' was created.")

        try:
            transmissionPowerLevelMax = TransmissionPowerLevel.objects.get(pk = "max")
            actionLog.append("Existing transmission-power-level 'max' was found.")
        except:
            transmissionPowerLevelMax = TransmissionPowerLevel(name = "max", value = 3)
            transmissionPowerLevelMax.save()
            actionLog.append("New transmission-power-level 'max' was created.")

        # :::::::::::::::::::::

        for i in range(CHANNEL_COUNT):
            try:
                channel = Channel.objects.get(number = i + 1)
                actionLog.append("Existing channel with number " + str(i + 1) + " was found.")
            except:
                channel = Channel(
                    number = i + 1,
                    enabled = False,
                    nickName = "Channel " + str(i + 1),
                    channelType = channelTypePump,
                    actionTriggerPercent = 50,
                    pumpDurationSeconds = 10,
                    sensorMeasureFrequencyMinutes = 60,
                    sensorTransmissionPowerLevel = transmissionPowerLevelMin,
                )
                channel.save()
                actionLog.append("New channel with number " + str(i + 1) + " was created.")

        # Remove any channels left over above the supported count (e.g. the
        # retired 6th channel) so databases initialized before the 5-channel
        # limit get cleaned up too.
        staleChannels = Channel.objects.filter(number__gt = CHANNEL_COUNT)
        for channel in staleChannels:
            number = channel.number
            channel.delete()
            actionLog.append("Removed unsupported channel with number " + str(number) + ".")

        return actionLog