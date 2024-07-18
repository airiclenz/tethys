from django.shortcuts import render
from django.db.models import Subquery
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
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
    ordering = ['number']

class ChannelRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    lookup_field = "number" 
    ordering = ['number']

class ChannelListView(generics.ListAPIView):
    serializer_class = ChannelSerializer
    queryset = Channel.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['number', 'nickName', 'channelType']
    ordering = ['number']

# /////////////////////////////////////////////////////////////////////////////
class ChannelSummaryView(generics.ListAPIView):
    serializer_class = ChannelSummarySerializer
    lastSensorData = SensorData.objects.last
    queryset = Channel.objects.all
    ordering = ['number']


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
class ScheduleListCreate(generics.ListCreateAPIView):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer

class ScheduleRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
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


# /////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////
class InitializeDatabaseView(APIView):
    def get(self, request, format=None):

        actionLog = ModelHelper.initializeDatabase();
        return Response(actionLog)