import os
import json
import requests

from datetime import datetime
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from djangoBase import settings, tools, jobs


lastUpdateLocal = None
isSilentPhaseLocal = None


class TethysConsumer(WebsocketConsumer):
    # ::::::::::::::::::::::::::::::::::::::::::
    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
            settings.CHANNEL_GROUP_NAME, self.channel_name
        )

        tools.log("Client CONNECT - " + self.channel_name)

        jobs.startPolling()

        self.accept()

    # ::::::::::::::::::::::::::::::::::::::::::
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            settings.CHANNEL_GROUP_NAME, self.channel_name
        )
        tools.log("Channel disconnected...")
        pass


    # ::::::::::::::::::::::::::::::::::::::::::
    # Receive message from WebSocket
    def receive(self, text_data):
        tools.log("Channel received web socket message: " + text_data)

        messageData = ""

        jsonData = json.loads(text_data)
        command = jsonData["command"]

        if command == "requestChannelSummary":
            messageData = tools.getResponseForSensorSummary()

        if command == "requestScheduleSummary":
            messageData = tools.getResponseForScheduleSummary()

        if command == "requestSystemStatus":
            messageData = tools.getReponseForSystemStatus()

        # answer to client
        self.send(text_data = messageData)

        pass

    # ::::::::::::::::::::::::::::::::::::::::::
    # Receive message from room group
    def channelSummary(self, event):
        message = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))


    # ::::::::::::::::::::::::::::::::::::::::::
    # Receive message from room group
    def scheduleSummary(self, event):
        message = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))
