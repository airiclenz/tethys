from django.db import models
import logging


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

    def __str__(self) -> str:
        return str(self.number) + ' - ' + self.nickName

# /////////////////////////////////////////////////////////////////////////////
class SensorData(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    batteryVoltage = models.FloatField()
    moisturePercent = models.SmallIntegerField()
    timestamp = models.DateTimeField(null=True)

    def __str__(self) -> str:
        return str(self.channel.number) + ' - ' + self.timestamp

# /////////////////////////////////////////////////////////////////////////////
class ActionLog(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    actionType = models.ForeignKey(ActionType, on_delete=models.DO_NOTHING)
    startTime = models.DateTimeField(null=True)
    endTime = models.DateTimeField(null=True)

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
            channelTypePump = channelTypePump(name = "pump")
            channelTypePump.save()
            actionLog.append("New channel-type 'pump' was created.")

        try:
            channelTypeValve = ChannelType.objects.get(pk = "valve")
            actionLog.append("Existing channel-type 'valve' was found.")
        except:
            channelTypeValve = channelTypePump(name = "valve")
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
        
        for i in range(5):
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

        return actionLog