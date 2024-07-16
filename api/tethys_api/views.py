from django.shortcuts import render
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
    lookup_field = "pk"

# /////////////////////////////////////////////////////////////////////////////
class ChannelTypeListCreate(generics.ListCreateAPIView):
    queryset = ChannelType.objects.all()
    serializer_class = ChannelTypeSerializer

class ChannelTypeRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChannelType.objects.all()
    serializer_class = ChannelTypeSerializer
    lookup_field = "pk"

# /////////////////////////////////////////////////////////////////////////////
class TransmissionPowerLevelListCreate(generics.ListCreateAPIView):
    queryset = TransmissionPowerLevel.objects.all()
    serializer_class = TransmissionPowerLevelSerializer

class TransmissionPowerLevelRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = TransmissionPowerLevel.objects.all()
    serializer_class = TransmissionPowerLevelSerializer
    lookup_field = "pk"