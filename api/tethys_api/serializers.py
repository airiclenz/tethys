from rest_framework import serializers
from .models import *


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
            'sensorTransmissionPowerLevel'
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

    sensorData_batteryVoltage = serializers.FloatField()
    sensorData_moisturePercent = serializers.IntegerField()
    sensorData_timestamp = serializers.DateTimeField()

    actionLog_actionType = serializers.CharField()
    actionLog_startTime = serializers.DateTimeField()
    actionLog_endTime = serializers.DateTimeField()


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


