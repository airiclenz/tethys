import os
import sys
from django.db.models import OuterRef, Subquery, F, Count
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import *
from .serializers import *
from .common import *
from .globals import setLastDataUpdate, getLastDataUpdate

# Get the absolute path of the core directory
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
# Append the core directory to sys.path
if root_path not in sys.path:
    sys.path.append(root_path)

# Now you can import hardware
import core.channel as hardwareChannel
import globals.config as tethysConfig


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def setLastDataUpdateNow():
    setLastDataUpdate()


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET'])
def initializeDatabase(request):

    print(f'{request.method} > ./api/initializeDatabase/')


    if request.method == 'GET':
        actionLog = ModelHelper.initializeDatabase();
        return Response(actionLog)
    

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET'])
def lastUpdate(request):

    print(f'> {request.method}  ./api/lastUpdate/')

    if request.method == 'GET':

        return Response({'timestamp': getLastDataUpdate()})


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET'])
def version(request):

    print(f'> {request.method}  ./api/version/')

    if request.method == 'GET':
    
        versionString = str(tethysConfig.version)

        return Response({'version': versionString})


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET'])
def silentPhaseStatus(request, timeZoneIdentifier):

    print(f'> {request.method}  ./api/silentPhaseStatus/{timeZoneIdentifier}')

    if request.method == 'GET':
        refreshSilentPhaseStatus(timeZoneIdentifier)
        return Response({
                'lastCalculationTime': str(SILENT_PHASE.lastCalculationTime),
                'startTime': str(SILENT_PHASE.startTime),
                'endTime': str(SILENT_PHASE.endTime),
                'inPhase': SILENT_PHASE.inPhase
            })

@api_view(['GET'])
def silentPhaseStatusForce(request, timeZoneIdentifier):

    print(f'> {request.method}  ./api/silentPhaseStatus/{timeZoneIdentifier}/force')

    if request.method == 'GET':
        refreshSilentPhaseStatus(timeZoneIdentifier, True)
        return Response({
                'lastCalculationTime': str(SILENT_PHASE.lastCalculationTime),
                'startTime': str(SILENT_PHASE.startTime),
                'endTime': str(SILENT_PHASE.endTime),
                'inPhase': SILENT_PHASE.inPhase
            })


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def actionLog(request):
    
    print(f'> {request.method}  ./api/actionLog/')

    if request.method == 'GET':
        records = ActionLog.objects.all()
        serializer = ActionLogSerializer(records, many=True)
        return Response({'actionLogs': serializer.data})
    
    elif request.method == 'POST':
        serializer = ActionLogSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        #if serializer.data.timestamp == None:
        serializer.timestamp = datetime.now()

        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'DELETE'])
def actionLog_single(request, number):
    
    print(f'> {request.method}  ./api/actionLog/{number}')

    try:
        records = ActionLog.objects.all().filter(channel = number)
    except ActionLog.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ActionLogSerializer(records, many=True)
        return Response({'actionLogs': serializer.data})

    elif request.method == 'DELETE':
        records.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_204_NO_CONTENT)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def actionType(request):
    
    print(f'> {request.method}  ./api/actionType/')

    if request.method == 'GET':
        records = ActionType.objects.all()
        serializer = ActionTypeSerializer(records, many=True)
        return Response({'actionTypes': serializer.data})
    
    elif request.method == 'POST':
        serializer = ActionTypeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def actionType_single(request, id):
    
    print(f'> {request.method}  ./api/actionType/{id}')

    try:
        record = ActionType.objects.get(pk = id)
    except ActionType.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ActionTypeSerializer(record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ActionTypeSerializer(record, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data)

    elif request.method == 'DELETE':
        record.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def channel(request):
    
    print(f'> {request.method}  ./api/channel/')

    if request.method == 'GET':
        records = Channel.objects.all()
        serializer = ChannelSerializer(records, many=True)
        return Response({'channels': serializer.data})
    
    elif request.method == 'POST':
        serializer = ChannelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def channel_single(request, number):

    print(f'> {request.method}  ./api/channel/{number}')

    try:
        record = Channel.objects.get(pk = number)
    except Channel.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ChannelSerializer(record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ChannelSerializer(record, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data)

    if request.method == 'DELETE':
        record.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_202_ACCEPTED)

@api_view(['PATCH'])
def channel_single_action(request, number, action):

    print(f'> {request.method}  ./api/channel/{number}/{action}')

    try:
        record = Channel.objects.get(pk = number)
    except Channel.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'PATCH':
        if record.enabled == False:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        
        if action == 'activate':
            hardwareChannel.setOutputState(
                number, 
                record.channelType.name, 
                True)
            
            return Response(status=status.HTTP_202_ACCEPTED) 
        
        elif action == 'deactivate':
            hardwareChannel.setOutputState(
                number, 
                record.channelType.name, 
                False)
            
            return Response(status=status.HTTP_202_ACCEPTED) 
        
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST) 


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET'])
def channelSummary(request):
    
    print(f'> {request.method}  ./api/channelSummary/')

    if request.method == 'GET':
        channels = Channel.objects.all()
        
        sensorData_subQuery = SensorData.objects.filter(channel=OuterRef('pk')).order_by('-timestamp')
        actionLog_subQuery = ActionLog.objects.filter(channel=OuterRef('pk')).order_by('-startTime')
        
        channels = channels.annotate(
                        
            sensorData_lastBatteryVoltage = Subquery(sensorData_subQuery.values('batteryVoltage')[:1]),
            sensorData_lastMoisturePercent = Subquery(sensorData_subQuery.values('moisturePercent')[:1]),
            sensorData_lastTimestamp = Subquery(sensorData_subQuery.values('timestamp')[:1]),
            sensorData_count = Subquery(sensorData_subQuery.values('id').annotate(count = Count('id')).values('count')),

            actionLog_lastActionType = Subquery(actionLog_subQuery.values('actionType')[:1]),
            actionLog_lastStartTime = Subquery(actionLog_subQuery.values('startTime')[:1]),
            actionLog_lastEndTime = Subquery(actionLog_subQuery.values('endTime')[:1]),
            actionLog_count = Subquery(actionLog_subQuery.values('id').annotate(count = Count('id')).values('count')),

            sensorTransmissionPowerLevelValue = F('sensorTransmissionPowerLevel__value')
        )

        for channel in channels:

            sensorDataSub = SensorData.objects.filter(channel = channel.number)
            channel.sensorData_count = sensorDataSub.count()

            actionLogSub = ActionLog.objects.filter(channel = channel.number)
            channel.actionLog_count = actionLogSub.count()


        serializer = ChannelSummarySerializer(channels, many=True)
        return Response({'channelSummaries': serializer.data})


@api_view(['GET'])
def channelSummary_single(request, number):
    
    print(f'> {request.method}  ./api/channelSummary/{number}')

    try:
        record = Channel.objects.get(pk = number)
    except Channel.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
       
        channels = Channel.objects.all()
        sensorData_subQuery = SensorData.objects.filter(channel=OuterRef('pk')).order_by('-timestamp')
        actionLog_subQuery = ActionLog.objects.filter(channel=OuterRef('pk')).order_by('-startTime')
        #sensorDataCount = sensorData.aggregate(total)

        channels = channels.annotate(
            sensorData_lastBatteryVoltage = Subquery(sensorData_subQuery.values('batteryVoltage')[:1]),
            sensorData_lastMoisturePercent = Subquery(sensorData_subQuery.values('moisturePercent')[:1]),
            sensorData_lastTimestamp = Subquery(sensorData_subQuery.values('timestamp')[:1]),
            sensorData_count = Subquery(sensorData_subQuery.values('id').annotate(count = Count('id')).values('count')),

            actionLog_lastActionType = Subquery(actionLog_subQuery.values('actionType')[:1]),
            actionLog_lastStartTime = Subquery(actionLog_subQuery.values('startTime')[:1]),
            actionLog_lastEndTime = Subquery(actionLog_subQuery.values('endTime')[:1]),
            actionLog_count = Subquery(actionLog_subQuery.values('id').annotate(count = Count('id')).values('count')),

            sensorTransmissionPowerLevelValue = F('sensorTransmissionPowerLevel__value')
        )

        for channel in channels:

            sensorDataSub = SensorData.objects.filter(channel = channel.number)
            channel.sensorData_count = sensorDataSub.count()

            actionLogSub = ActionLog.objects.filter(channel = channel.number)
            channel.actionLog_count = actionLogSub.count()

        record = channels.filter(pk = number)[0]
        serializer = ChannelSummarySerializer(record)
        return Response(serializer.data)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def channelType(request):
    
    print(f'> {request.method}  ./api/channelType/')

    if request.method == 'GET':
        records = ChannelType.objects.all()
        serializer = ChannelTypeSerializer(records, many=True)
        return Response({'channelTypes': serializer.data})
    
    elif request.method == 'POST':
        serializer = ChannelTypeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def channelType_single(request, id):

    print(f'> {request.method}  ./api/channelType/{id}')

    try:
        record = ChannelType.objects.get(pk = id)
    except ChannelType.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ChannelTypeSerializer(record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ChannelTypeSerializer(record, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data)

    if request.method == 'DELETE':
        record.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_202_ACCEPTED)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def sensorData(request):

    print(f'> {request.method}  ./api/sensorData/')

    if request.method == 'GET':
        records = SensorData.objects.all()
        serializer = SensorDataSerializer(records, many=True)
        return Response({'sensorData': serializer.data})
    
    elif request.method == 'POST':
        serializer = SensorDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE'])
def sensorData_single(request, number):

    print(f'> {request.method}  ./api/sensorData/{number}')

    try:
        records = SensorData.objects.all().filter(channel=number)
    except SensorData.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = SensorDataSerializer(records, many=True)
        return Response({'sensorData': serializer.data})

    elif request.method == 'DELETE':
        records.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_204_NO_CONTENT)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def schedule(request):
    
    print(f'> {request.method}  ./api/schedule/')

    if request.method == 'GET':
        records = Schedule.objects.all()
        serializer = ScheduleSerializer(records, many=True)
        return Response({'schedules': serializer.data})
    
    elif request.method == 'POST':
        serializer = ScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def schedule_single(request, id):

    print(f'> {request.method}  ./api/schedule/{id}')

    try:
        record = Schedule.objects.get(pk = id)
    except Schedule.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ScheduleSerializer(record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ScheduleSerializer(record, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data)

    elif request.method == 'DELETE':
        record.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_204_NO_CONTENT)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def scheduleType(request):
    
    print(f'> {request.method}  ./api/scheduleType/')

    if request.method == 'GET':
        records = ScheduleType.objects.all()
        serializer = ScheduleTypeSerializer(records, many=True)
        return Response({'scheduleTypes': serializer.data})
    
    elif request.method == 'POST':
        serializer = ScheduleTypeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def scheduleType_single(request, id):

    print(f'> {request.method}  ./api/scheduleType/{id}')

    try:
        record = ScheduleType.objects.get(pk = id)
    except ScheduleType.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ScheduleTypeSerializer(record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ScheduleTypeSerializer(record, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data)

    if request.method == 'DELETE':
        record.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_202_ACCEPTED)


# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@api_view(['GET', 'POST'])
def transmissionPowerLevel(request):
    
    print(f'> {request.method}  ./api/transmissionPowerLevel/')

    if request.method == 'GET':
        records = TransmissionPowerLevel.objects.all()
        serializer = TransmissionPowerLevelSerializer(records, many=True)
        return Response({'transmissionPowerLevels': serializer.data})
    
    elif request.method == 'POST':
        serializer = TransmissionPowerLevelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
def transmissionPowerLevel_single(request, id):

    print(f'> {request.method}  ./api/transmissionPowerLevel/{id}')

    try:
        record = TransmissionPowerLevel.objects.get(pk = id)
    except TransmissionPowerLevel.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = TransmissionPowerLevelSerializer(record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = TransmissionPowerLevelSerializer(record, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        setLastDataUpdateNow()
        return Response(serializer.data)

    if request.method == 'DELETE':
        record.delete()
        setLastDataUpdateNow()
        return Response(status=status.HTTP_202_ACCEPTED)







