from django.utils import timezone
from rest_framework import serializers
from .models import *
from . import firmware


# /////////////////////////////////////////////////////////////////////////////
class ActionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionType
        fields = [
            'name'
        ]

# /////////////////////////////////////////////////////////////////////////////
class ChannelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelType
        fields = [
            'name'
        ]

# /////////////////////////////////////////////////////////////////////////////
class TransmissionPowerLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransmissionPowerLevel
        fields = [
            'name',
            'value'
        ]

# /////////////////////////////////////////////////////////////////////////////
class ScheduleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleType
        fields = [
            'name'
        ]

# /////////////////////////////////////////////////////////////////////////////
class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = [
            'number', 
            'enabled', 
            'nickName', 
            'channelType', 
            'actionTriggerPercent',
            'pumpDurationSeconds',
            'sensorMeasureFrequencyMinutes',
            'sensorTriggerCalibration',
            'sensorTransmissionPowerLevel',
            'sensorFirmwareVersion'
        ]


# /////////////////////////////////////////////////////////////////////////////
class ChannelSummarySerializer(serializers.Serializer):

    number = serializers.IntegerField()
    enabled = serializers.BooleanField() 
    nickName = serializers.CharField()
    channelType = serializers.CharField() 
    actionTriggerPercent = serializers.IntegerField()
    pumpDurationSeconds = serializers.IntegerField()
    sensorMeasureFrequencyMinutes = serializers.IntegerField()
    sensorTriggerCalibration = serializers.BooleanField()
    sensorTransmissionPowerLevel = serializers.CharField()
    sensorTransmissionPowerLevelValue = serializers.IntegerField()
    sensorFirmwareVersion = serializers.CharField(allow_blank=True, allow_null=True)
    # Derived (not stored): the latest firmware version the master reads from the
    # sensor source (wpw_Version.h) and how this channel's reported version
    # compares to it, so the UI can show an up-to-date / outdated hint. The
    # latest value is read once per request and passed in via the serializer
    # context (see the channelSummary views).
    latestFirmwareVersion = serializers.SerializerMethodField()
    firmwareStatus = serializers.SerializerMethodField()

    sensorData_lastBatteryVoltage = serializers.FloatField()
    sensorData_lastMoisturePercent = serializers.IntegerField()
    sensorData_lastTimestamp = serializers.DateTimeField()
    sensorData_count = serializers.IntegerField()

    actionLog_lastActionType = serializers.CharField()
    actionLog_lastStartTime = serializers.DateTimeField()
    actionLog_lastEndTime = serializers.DateTimeField()
    actionLog_count = serializers.IntegerField()

    def get_latestFirmwareVersion(self, obj):
        return self.context.get("latestFirmwareVersion") or ""

    def get_firmwareStatus(self, obj):
        reported = getattr(obj, "sensorFirmwareVersion", "") or ""
        if not reported:
            return "unknown"
        return firmware.firmware_status(
            reported, self.context.get("latestFirmwareVersion"))


# /////////////////////////////////////////////////////////////////////////////
class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = [
            'id', 
            'channel',
            'batteryVoltage',
            'moisturePercent',
            'timestamp'
        ]


# /////////////////////////////////////////////////////////////////////////////
class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = [
            'id', 
            'channel',
            'actionType',
            'startTime',
            'endTime'
        ]


# /////////////////////////////////////////////////////////////////////////////
class ScheduleSerializer(serializers.ModelSerializer):

    # id = serializers.IntegerField()

    class Meta:
        model = Schedule
        fields = [
            'id',
            'weekday',
            'enabled',
            'scheduleType',
            'startTime',
            'durationMinutes'
        ]


# /////////////////////////////////////////////////////////////////////////////
class ManualCommandSerializer(serializers.ModelSerializer):

    # Flatten the related channel so the core gets the number and the pump type
    # it needs to drive the controller, without a second lookup.
    channel = serializers.IntegerField(source='channel.number', read_only=True)
    channelType = serializers.CharField(source='channel.channelType.name', read_only=True)
    # Age computed on the API side (same clock and timezone setting as the stored
    # timestamp), so the core just applies its freshness policy to a plain number.
    ageSeconds = serializers.SerializerMethodField()

    class Meta:
        model = ManualCommand
        fields = [
            'id',
            'channel',
            'channelType',
            'action',
            'status',
            'message',
            'requestedAt',
            'ageSeconds',
        ]

    def get_ageSeconds(self, obj):
        return (timezone.now() - obj.requestedAt).total_seconds()


