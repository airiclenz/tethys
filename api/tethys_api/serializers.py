from rest_framework import serializers
from tethys_api.models import *


# /////////////////////////////////////////////////////////////////////////////
class ActionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionType
        fields = [
            "name"
        ]

# /////////////////////////////////////////////////////////////////////////////
class ChannelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelType
        fields = [
            "name"
        ]

# /////////////////////////////////////////////////////////////////////////////
class TransmissionPowerLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransmissionPowerLevel
        fields = [
            "name",
            "value"
        ]

# /////////////////////////////////////////////////////////////////////////////
class ScheduleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleType
        fields = [
            "name"
        ]

# /////////////////////////////////////////////////////////////////////////////
class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = [
            "id", 
            "number", 
            "enabled", 
            "nickName", 
            "channelType", 
            "actionTriggerPercent",
            "pumpDurationSeconds",
            "sensorMeasureFrequencyMinutes",
            "sensorTriggerCalibration",
            "sensorTransmissionPowerLevel"]
        channelType = ChannelTypeSerializer
        
# /////////////////////////////////////////////////////////////////////////////
class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = [
            "id", 
            "channel",
            "batteryVoltage",
            "moisturePercent",
            "timestamp"]


# /////////////////////////////////////////////////////////////////////////////
class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = [
            "id", 
            "channel",
            "actionType",
            "startTime",
            "endTime"]


# /////////////////////////////////////////////////////////////////////////////
class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = [
            "id", 
            "weekday",
            "enabled",
            "scheduleType",
            "startTime",
            "duration"]


