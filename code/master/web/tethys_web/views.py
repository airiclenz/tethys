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
