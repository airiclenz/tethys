from django.urls import include, path
from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [

    path("", RedirectView.as_view(url="channels/", permanent=False), name="channels"),
    path("channels/", views.channels, name="channels"),
    path("schedules/", views.schedules, name="schedules"),
    path("measurements/", views.measurements, name="measurements"),
    path("actions/", views.actions, name="actions"),
    path("webcam/", views.webcam, name="webcam")

]
