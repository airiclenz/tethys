
from django.contrib import admin
from .models import *

admin.site.register([
    ActionLog,
    ActionType, 
    Channel,
    ChannelType,
    Schedule,
    ScheduleType,
    TransmissionPowerLevel   
])