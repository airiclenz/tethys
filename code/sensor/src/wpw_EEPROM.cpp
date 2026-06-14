

#include <Arduino.h>
#include <EEPROM.h>

#include "bitOps.h"

#include <wpw_Blinker.h>
#include <wpw_Config.h>
#include <wpw_EEPROM.h>
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

		SaveCalibrationToEeprom();
	}
	else
	{
		ReadSettingsFromEeprom();

		ReadCalibrationFromEeprom();
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
	DoSimpleBlink(150, 300);
	DoSimpleBlink(100, 200);
	DoSimpleBlink( 75, 150);
	DoSimpleBlink( 50, 100);
	DoSimpleBlink( 25,  75);
	DoSimpleBlink( 15,  50);
	DoSimpleBlink(300,  50);
}



// =============================================================================
// Mirror image of BlinkEepromSaveSuccess(): a decelerating ramp (fast -> slow)
// that fades out WITHOUT the terminal long flash. "Ramp up to a strong finish"
// = something was committed; "ramp down to nothing" = nothing changed.
void BlinkEepromNoChange()
{
	DoSimpleBlink( 15,  50);
	DoSimpleBlink( 25,  75);
	DoSimpleBlink( 50, 100);
	DoSimpleBlink( 75, 150);
	DoSimpleBlink(100, 200);
	DoSimpleBlink(150, 300);
}


// =============================================================================
void SaveSettingsToEeprom(bool showFeedback)
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

		
		if (showFeedback)
		{
			if (settingsChanged)
			{
				BlinkEepromSaveSuccess();
			}
			else
			{
				BlinkEepromNoChange();
			}
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

