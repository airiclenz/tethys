# chat/views.py
import requests

from urllib.parse import urlparse
from django.shortcuts import render
from djangoBase import tools


# ::::::::::::::::::::::::::::::::::
def channels(request):
    
    pathApi = tools.getApiPathFromRequest(request)

    tools.log("API-PATH: " + pathApi)

    try:
        response = requests.get(pathApi + "channelsummary")
    except requests.exceptions.RequestException:
        return render(request, "./error/error-api.html")

    channelSummaries = response.json()[1]["channelSummary"]
    
    context = {
        "title": "Tethys", 
        "channels": channelSummaries
    }

    return render(request, "index-channels.html", context)


# ::::::::::::::::::::::::::::::::::
def schedules(request):

    pathApi = tools.getApiPathFromRequest(request)

    tools.log("API-PATH: " + pathApi)

    try:
        response = requests.get(pathApi + "schedule/")
    except requests.exceptions.RequestException:
        return render(request, "./error/error-api.html")

    schedules = response.json()["schedule"]
    context = {"title": "Tethys", "schedules": schedules}

    return render(request, "index-schedules.html", context)
