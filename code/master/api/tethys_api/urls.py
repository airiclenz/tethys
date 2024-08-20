from django.contrib import admin
from django.urls import path
from tethys_api import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/lastUpdate/', views.lastUpdate),

    path('api/version/', views.version),

    path('api/silentPhaseStatus/<str:timeZoneIdentifier>', views.silentPhaseStatus),
    path('api/silentPhaseStatus/<str:timeZoneIdentifier>/force', views.silentPhaseStatusForce),

    path('api/initializeDatabase/', views.initializeDatabase),

    path('api/actionLog/', views.actionLog),
    path('api/actionLog/<str:number>', views.actionLog_single),

    path('api/actionType/', views.actionType),
    path('api/actionType/<str:id>', views.actionType_single),

    path('api/channel/', views.channel),
    path('api/channel/<str:number>', views.channel_single),
    path('api/channel/<str:number>/<str:action>', views.channel_single_action),

    path('api/channelSummary/', views.channelSummary),
    path('api/channelSummary/<int:number>', views.channelSummary_single),

    path('api/channelType/', views.channelType),
    path('api/channelType/<str:id>', views.channelType_single),

    path('api/sensorData/', views.sensorData),
    path('api/sensorData/<int:number>', views.sensorData_single),

    path('api/schedule/', views.schedule),
    path('api/schedule/<int:id>', views.schedule_single),

    path('api/scheduleType/', views.scheduleType),
    path('api/scheduleType/<str:id>', views.scheduleType_single),

    path('api/transmissionPowerLevel/', views.transmissionPowerLevel),
    path('api/transmissionPowerLevel/<str:id>', views.transmissionPowerLevel_single),
]
