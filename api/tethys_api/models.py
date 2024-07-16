from django.db import models


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
    '''The svsilsblr action types.'''
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name

# /////////////////////////////////////////////////////////////////////////////
class ChannelType(models.Model):
    '''The available channel types'''
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name

# /////////////////////////////////////////////////////////////////////////////
class TransmissionPowerLevel(models.Model):
    '''The available transmission-power-levels'''
    name = models.CharField(max_length=100, unique=True)
    value = models.IntegerField(unique = True);

    def __str__(self) -> str:
            return self.name

# /////////////////////////////////////////////////////////////////////////////
class ScheduleType(models.Model):
    '''The available schedule-types'''
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name

# /////////////////////////////////////////////////////////////////////////////
class Channel(models.Model):
    '''All existing channels'''
    number = models.IntegerField(unique=True)
    enabled = models.BooleanField(default=False)
    nickName = models.CharField(max_length=100, blank=True, default="New Channel")
    channelType = models.ForeignKey(ChannelType, on_delete=models.DO_NOTHING)
    actionTriggerPercent = models.IntegerField()
    pumpDurationSeconds = models.IntegerField()
    sensorMeasureFrequencyMinutes = models.IntegerField()
    sensorTriggerCalibration = models.BooleanField()
    sensorTransmissionPowerLevel = models.ForeignKey(TransmissionPowerLevel, on_delete=models.DO_NOTHING)

    def __str__(self) -> str:
        return self.number + ' - ' + self.nickName

# /////////////////////////////////////////////////////////////////////////////
class SensorData(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    batteryVoltage = models.FloatField()
    moisturePercent = models.SmallIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.channel.number + ' - ' + self.timestamp

# /////////////////////////////////////////////////////////////////////////////
class ActionLog(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    actionType = models.ForeignKey(ActionType, on_delete=models.DO_NOTHING)
    startTime = models.DateTimeField(auto_now_add=True)
    endTime = models.DateTimeField(null=True)

    def __str__(self) -> str:
        return self.channel.number + ' - ' + self.actionType.name


# /////////////////////////////////////////////////////////////////////////////
class Schedule(models.Model):
    enabled = models.BooleanField(default=True)
    weekday = models.CharField(max_length=20, choices=WEEKDAYS)
    scheduleType = models.ForeignKey(ScheduleType, on_delete=models.DO_NOTHING)
    startTime = models.DateTimeField()
    duration = models.SmallIntegerField()

    def __str__(self) -> str:
        return self.weekday + ' - ' + self.scheduleType.name
