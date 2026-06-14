

#include <Arduino.h>
#include <EEPROM.h>

#include "bitOps.h"

#include <wpw_Blinker.h>
#include <wpw_Config.h>
#include <wpw_EEPROM.h>
#include <wpw_Input.h>
#include <wpw_UI.h>
#include <wpw_RXTX.h>
#include <wpw_Sensor.h>
#include <wpw_Version.h>
#include <wpw_WirelessPlantWatering.h>




bool _dirty = false;




// =============================================================================
void InitializeEeprom()
{
	EEPROM.begin();

	uint8_t version;
	uint8_t subversion;

	EEPROM.get(0, version);
	EEPROM.get(1, subversion);

	if (version != VERSION ||
		subversion != SUBVERSION)
	{
		EEPROM.put(0, (uint8_t)VERSION);
		EEPROM.put(1, (uint8_t)SUBVERSION);

		_dirty = true;
		SaveSettingsToEeprom();

		#ifdef TX
			SaveCalibrationToEeprom();
		#endif
	}
	else
	{
		ReadSettingsFromEeprom();

		#ifdef TX
			ReadCalibrationFromEeprom();
		#endif
	}

}


// =============================================================================
void MakeSettingsFlagDirty()
{
	_dirty = true;
}


// =============================================================================
bool IsSettingsFlagDirty()
{
	return _dirty;
}


// =============================================================================
void BlinkEepromSaveSuccess()
{
	#ifdef TX
		DoSimpleBlink(150, 300);
		DoSimpleBlink(100, 200);
		DoSimpleBlink( 75, 150);
		DoSimpleBlink( 50, 100);
		DoSimpleBlink( 25,  75);
		DoSimpleBlink( 15,  50);
		DoSimpleBlink(300,  50);
	#endif

	#ifdef RX
		AddBlinkToQueue(150, 300);
		AddBlinkToQueue(100, 200);
		AddBlinkToQueue( 75, 150);
		AddBlinkToQueue( 50, 100);
		AddBlinkToQueue( 25,  75);
		AddBlinkToQueue( 15,  50);
		AddBlinkToQueue(300,  50);
	#endif

}



// =============================================================================
// Mirror image of BlinkEepromSaveSuccess(): a decelerating ramp (fast -> slow)
// that fades out WITHOUT the terminal long flash. "Ramp up to a strong finish"
// = something was committed; "ramp down to nothing" = nothing changed.
void BlinkEepromNoChange()
{
	#ifdef TX
		DoSimpleBlink( 15,  50);
		DoSimpleBlink( 25,  75);
		DoSimpleBlink( 50, 100);
		DoSimpleBlink( 75, 150);
		DoSimpleBlink(100, 200);
		DoSimpleBlink(150, 300);
	#endif

	#ifdef RX
		AddBlinkToQueue( 15,  50);
		AddBlinkToQueue( 25,  75);
		AddBlinkToQueue( 50, 100);
		AddBlinkToQueue( 75, 150);
		AddBlinkToQueue(100, 200);
		AddBlinkToQueue(150, 300);
	#endif

}



#ifdef RX


	// =============================================================================
	void SaveSettingsToEeprom()
	{
		if (_dirty)
		{
			uint16_t address = 8;
			uint16_t * displayTimeOut = GetDisplayTimeoutPointer();
			uint8_t * transmissionPower = GetTransmissionPowerPointer();
			bool * useWaterSensorPtr = GetUseWaterSensorPointer();


			EEPROM.put(address, (uint16_t)*displayTimeOut);				address += sizeof(*displayTimeOut);
			EEPROM.put(address, (uint8_t)*transmissionPower);			address += sizeof(*transmissionPower);
			EEPROM.put(address, *useWaterSensorPtr);						address += sizeof(*useWaterSensorPtr);


			for (uint8_t i=0; i<SENSOR_COUNT; i++)
			{
				Sensor * sensorsPtr = GetSensorPointer(i);

				// get every channel from the next 32er slot... eg: 32, 64, ...
				address = (i+1) * 32;

				EEPROM.put(address, (*sensorsPtr).Status);				address += sizeof((*sensorsPtr).Status);
				EEPROM.put(address, (*sensorsPtr).MeasureFrequency);		address += sizeof((*sensorsPtr).MeasureFrequency);
				EEPROM.put(address, (*sensorsPtr).PumpDuration);			address += sizeof((*sensorsPtr).PumpDuration);
				EEPROM.put(address, (*sensorsPtr).TriggerLevel);			address += sizeof((*sensorsPtr).TriggerLevel);
				EEPROM.put(address, (*sensorsPtr).TransmissionPower);	address += sizeof((*sensorsPtr).TransmissionPower);

			}

			BlinkEepromSaveSuccess();

			_dirty = false;
		}
	}



	// =============================================================================
	void ReadSettingsFromEeprom()
	{
		uint16_t address = 8;
		uint16_t * displayTimeOut = GetDisplayTimeoutPointer();
		uint8_t * transmissionPower = GetTransmissionPowerPointer();
		bool * useWaterSensorPtr = GetUseWaterSensorPointer();


		EEPROM.get(address, *displayTimeOut);								address += sizeof(*displayTimeOut);
		EEPROM.get(address, *transmissionPower);							address += sizeof(*transmissionPower);
		EEPROM.get(address, *useWaterSensorPtr);							address += sizeof(*useWaterSensorPtr);


		for (uint8_t i=0; i<SENSOR_COUNT; i++)
		{
			Sensor * sensorsPtr = GetSensorPointer(i);

			// get every channel from the next 32er slot... eg: 32, 64, ...
			address = (i+1) * 32;

			EEPROM.get(address, (*sensorsPtr).Status);						address += sizeof((*sensorsPtr).Status);
			EEPROM.get(address, (*sensorsPtr).MeasureFrequency);			address += sizeof((*sensorsPtr).MeasureFrequency);
			EEPROM.get(address, (*sensorsPtr).PumpDuration);				address += sizeof((*sensorsPtr).PumpDuration);
			EEPROM.get(address, (*sensorsPtr).TriggerLevel);				address += sizeof((*sensorsPtr).TriggerLevel);
			EEPROM.get(address, (*sensorsPtr).TransmissionPower);			address += sizeof((*sensorsPtr).TransmissionPower);

			deleteBit((*sensorsPtr).Status, CHANNEL_BATTERY_ALERT);
			deleteBit((*sensorsPtr).Status, CHANNEL_CHECK_PUMP);
			deleteBit((*sensorsPtr).Status, CHANNEL_CALIBRATE);

		}

		_dirty = false;

		AddBlinkToQueue(50, 100);
		AddBlinkToQueue(50, 100);
		AddBlinkToQueue(400, 100);

	}


#endif


#ifdef TX

	// =============================================================================
	void SaveSettingsToEeprom()
	{
		if (_dirty)
		{
			uint16_t address = 8;

			uint16_t * loops = GetWatchdogLoopPointer();
			uint8_t  * transmissionPower = GetTransmissionPowerPointer();
			
			uint8_t tempInt8;
			uint16_t tempInt16;

			bool settingsChanged = false;

			EEPROM.get(address, tempInt16);
			if (tempInt16 != *loops)
			{
				EEPROM.put(address, *loops);
				settingsChanged = true;							
			}
			address += 2;


			EEPROM.get(address, tempInt8);
			if (tempInt8 != *transmissionPower)
			{
				EEPROM.put(address, *transmissionPower);
				settingsChanged = true;
			}
			address += 1;

			
			if (settingsChanged)
			{
				BlinkEepromSaveSuccess();
			}
			else
			{
				BlinkEepromNoChange();
			}
			

			_dirty = false;
		}
	}




	// =============================================================================
	void ReadSettingsFromEeprom()
	{
		uint16_t address = 8;

		uint16_t * loops = GetWatchdogLoopPointer();
		uint8_t  * transmissionPower = GetTransmissionPowerPointer();

		EEPROM.get(address, *loops);							address += sizeof(*loops);
		EEPROM.get(address, *transmissionPower);				address += sizeof(*transmissionPower);

		_dirty = false;
	}


	// =============================================================================
	void SaveCalibrationToEeprom()
	{
		uint16_t address = 32;

		CalibrationData * calibration = GetCalibrationPointer();

		EEPROM.put(address, (*calibration).MinimumValue);	address += sizeof((*calibration).MinimumValue);
		EEPROM.put(address, (*calibration).MaximumValue);	address += sizeof((*calibration).MaximumValue);
	}


	// =============================================================================
	void ReadCalibrationFromEeprom()
	{
		uint16_t address = 32;

		CalibrationData * calibration = GetCalibrationPointer();

		EEPROM.get(address, (*calibration).MinimumValue);		address += sizeof((*calibration).MinimumValue);
		EEPROM.get(address, (*calibration).MaximumValue);		address += sizeof((*calibration).MaximumValue);
	}

#endif