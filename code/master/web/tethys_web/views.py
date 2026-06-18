# chat/views.py
import requests
import json

from urllib.parse import urlparse
from django.shortcuts import render
from . import tools


# ::::::::::::::::::::::::::::::::::
def channels(request):
    '''
    pathApi = tools.getApiPathFromRequest(request)

    tools.log("API-PATH: " + pathApi)

    try:
        response = requests.get(pathApi + "channelSummary/")
    except requests.exceptions.RequestException:
        return render(request, "./error/error-api.html")

    if response.status_code != 200:
        return render(request, "./error/error-api.html")
    
    channelSummaries = response.json()['channelSummaries']
    '''

    context = {
        "title": "Tethys", 
        "channels": None #channelSummaries
    }

    return render(request, "index-channels.html", context)


# ::::::::::::::::::::::::::::::::::
def schedules(request):
    '''
    pathApi = tools.getApiPathFromRequest(request)

    tools.log("API-PATH: " + pathApi)

    try:
        response = requests.get(pathApi + "schedule/")
    except requests.exceptions.RequestException:
        return render(request, "./error/error-api.html")

    schedules = response.json()
    '''

    context = {
        "title": "Tethys",
        "schedules": None #schedules
    }

    return render(request, "index-schedules.html", context)


# ::::::::::::::::::::::::::::::::::
def measurements(request):
    # The page fetches its sensor readings client-side via the REST API
    # (per channel, see static/ts/measurements.ts), so the view only renders
    # the template shell.
    context = {
        "title": "Tethys"
    }

    return render(request, "index-measurements.html", context)


# ::::::::::::::::::::::::::::::::::
def actions(request):
    # The page fetches its action log client-side via the REST API
    # (per channel, see static/ts/actions.ts), so the view only renders
    # the template shell.
    context = {
        "title": "Tethys"
    }

    return render(request, "index-actions.html", context)


# ::::::::::::::::::::::::::::::::::
def webcam(request):
    # The page talks to the separate tethys-camera service client-side over
    # /camera/ (enable, snapshot polling — see static/ts/webcam.ts), so the view
    # only renders the template shell.
    context = {
        "title": "Tethys"
    }

    return render(request, "index-webcam.html", context)
