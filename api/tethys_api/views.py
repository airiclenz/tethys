from django.shortcuts import render
#from rest_framework_swagger.views import get_swagger_view
from rest_framework import generics
from tethys_api.models import *
from tethys_api.serializers import *


# /////////////////////////////////////////////////////////////////////////////
class ActionTypeListCreate(generics.ListCreateAPIView):
    queryset = ActionType.objects.all()
    serializer_class = ActionTypeSerializer

class ActionTypeRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActionType.objects.all()
    serializer_class = ActionTypeSerializer
    lookup_field = "name"


# /////////////////////////////////////////////////////////////////////////////
class ChannelListCreate(generics.ListCreateAPIView):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer

class ChannelRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    lookup_field = "pk" 


# /////////////////////////////////////////////////////////////////////////////
class ChannelTypeListCreate(generics.ListCreateAPIView):
    queryset = ChannelType.objects.all()
    serializer_class = ChannelTypeSerializer

class ChannelTypeRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChannelType.objects.all()
    serializer_class = ChannelTypeSerializer
    lookup_field = "name"

# /////////////////////////////////////////////////////////////////////////////
class SensorDataListCreate(generics.ListCreateAPIView):
    queryset = SensorData.objects.all()
    serializer_class = SensorDataSerializer

class SensorDataRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = SensorData.objects.all()
    serializer_class = SensorDataSerializer
    lookup_field = "pk"


# /////////////////////////////////////////////////////////////////////////////
class ScheduleTypeListCreate(generics.ListCreateAPIView):
    queryset = ScheduleType.objects.all()
    serializer_class = ScheduleTypeSerializer

class ScheduleTypeRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleType.objects.all()
    serializer_class = ScheduleTypeSerializer
    lookup_field = "pk"


# /////////////////////////////////////////////////////////////////////////////
class TransmissionPowerLevelListCreate(generics.ListCreateAPIView):
    queryset = TransmissionPowerLevel.objects.all()
    serializer_class = TransmissionPowerLevelSerializer

class TransmissionPowerLevelRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = TransmissionPowerLevel.objects.all()
    serializer_class = TransmissionPowerLevelSerializer
    lookup_field = "pk"

