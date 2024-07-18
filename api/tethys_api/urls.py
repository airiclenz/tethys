from django.urls import path
from . import views


urlpatterns = [
    path("actionType/", views.ActionTypeListCreate.as_view(), name="actionType-create-view"),
    path("actionType/<str:name>", views.ActionTypeRetrieveUpdateDestroy.as_view(), name="actionType-retrieve-update-detroy"),

    path("channel/", views.ChannelListCreate.as_view(), name="channel-create-view"),
    path("channel/<int:number>", views.ChannelRetrieveUpdateDestroy.as_view(), name="channel-retrieve-update-detroy"),
    #path("channel/", views.ChannelListView.as_view(), name="channel-filtered-list-view"),

    path("channelSummary/", views.ChannelSummaryView.as_view(), name="channelSummary-view"),

    path("channelType/", views.ChannelTypeListCreate.as_view(), name="channelType-create-view"),
    path("channelType/<str:name>", views.ChannelTypeRetrieveUpdateDestroy.as_view(), name="channelType-retrieve-update-detroy"),
    
    path("sensorData/", views.SensorDataListCreate.as_view(), name="sensorData-create-view"),
    path("sensorData/<int:pk>", views.SensorDataRetrieveUpdateDestroy.as_view(), name="sensorData-retrieve-update-detroy"),

    path("schedule/", views.ScheduleListCreate.as_view(), name="schedule-create-view"),
    path("schedule/<int:pk>", views.ScheduleRetrieveUpdateDestroy.as_view(), name="schedule-retrieve-update-detroy"),

    path("scheduleType/", views.ScheduleTypeListCreate.as_view(), name="scheduleType-create-view"),
    path("scheduleType/<str:name>", views.ScheduleTypeRetrieveUpdateDestroy.as_view(), name="scheduleType-retrieve-update-detroy"),

    path("transmissionPowerLevel/", views.TransmissionPowerLevelListCreate.as_view(), name="transmissionPowerLevel-create-view"),
    path("transmissionPowerLevel/<str:name>", views.TransmissionPowerLevelRetrieveUpdateDestroy.as_view(), name="transmissionPowerLevel-retrieve-update-detroy"),
    path("transmissionPowerLevel/<int:value>", views.TransmissionPowerLevelRetrieveUpdateDestroy.as_view(), name="transmissionPowerLevel-retrieve-update-detroy"),

    path("initializeDatabase/", views.InitializeDatabaseView.as_view(), name="initialize-database-view"),
]
