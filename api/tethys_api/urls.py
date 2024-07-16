from django.urls import path
from . import views


urlpatterns = [
    path("actionType/", views.ActionTypeListCreate.as_view(), name="actionType-create-view"),
    path("actionType/<int:pk>", views.ActionTypeRetrieveUpdateDestroy.as_view(), name="actionType-retrieve-update-detroy"),

    path("channelType/", views.ChannelTypeListCreate.as_view(), name="channelType-create-view"),
    path("channelType/<int:pk>", views.ChannelTypeRetrieveUpdateDestroy.as_view(), name="channelType-retrieve-update-detroy"),

    path("transmissionPowerLevel/", views.TransmissionPowerLevelListCreate.as_view(), name="transmissionPowerLevel-create-view"),
    path("transmissionPowerLevel/<int:pk>", views.TransmissionPowerLevelRetrieveUpdateDestroy.as_view(), name="transmissionPowerLevel-retrieve-update-detroy"),
]