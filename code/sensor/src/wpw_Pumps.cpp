

#include <bitOps.h>

#include "wpw_Config.h"

#include "wpw_Blinker.h"
#include "wpw_Input.h"
#include "wpw_Pumps.h"
#include "wpw_RXTX.h"
#include "wpw_Sensor.h"
#include "wpw_UI.h"



#ifdef RX


	// ============================================================================
	void HandlePumpsAndValves()
	{

		bool * useWaterSensorPtr = GetUseWaterSensorPointer();

		// if the water sensor returns a bad value AND
		// we are supposed to use it:
		if (!IsWaterOk() &&
			*useWaterSensorPtr)
		{
			ReadWaterSensor();
			return;
		}


		// if we are not in the seetings menu
		if (!InSettingsMenu())
		{

			// loop all our channels
			for (uint8_t chNr=1; chNr<=SENSOR_COUNT; chNr++)
			{
				Sensor * sensorsPtr = GetSensorPointer(chNr-1);

				// only continue if the channel is enabled
				// and the moisture-level is equal or below the trigger-level:
				if (isBit((*sensorsPtr).Status, CHANNEL_ENABLED) &&
					isBit((*sensorsPtr).Status, CHANNEL_CHECK_PUMP) &&
					(*sensorsPtr).MoistureLevel <= (*sensorsPtr).TriggerLevel)
				{

					// VALVE
					if (isBit((*sensorsPtr).Status, CHANNEL_TYPE_ISVALVE))
					{
						SetValveStatus(chNr, HIGH);

						HandleReceiver();
						HandleBlinks();

						DoPumping(
							chNr,
							6,
							(*sensorsPtr).PumpDuration);

						HandleReceiver();
						HandleBlinks();

						SetValveStatus(chNr, LOW);
					}

					// PUMP
					else
					{
						DoPumping(
							chNr,
							chNr,
							(*sensorsPtr).PumpDuration);
					}

					(*sensorsPtr).PumpCount++;

					RegisterDisplayRefresh();

				}

				deleteBit((*sensorsPtr).Status, CHANNEL_CHECK_PUMP);

			} // loop

		} // not in settings menu

	}


	// ============================================================================
	void DoPumping(
		uint8_t channelNumber,
		uint8_t portNumber,
		uint16_t durationSec
		)
	{

		uint32_t duration = (uint32_t)durationSec * (uint32_t)1000;
		uint32_t lastdisplayUpdate = 0;
		uint32_t remainingTime = duration;
		uint32_t startTime = millis();

		SetValveStatus(portNumber, HIGH);

		while (millis() < (startTime + duration))
		{

			HandleReceiver();
			HandleBlinks();

			if (millis() > (lastdisplayUpdate + 1000))
			{
				PaintPumpingScreen(
					channelNumber,
					portNumber,
					remainingTime);

				remainingTime = startTime + duration - millis();
				lastdisplayUpdate = millis();
			}

			// Abort on Button Press
			if (IsButton1Press() ||
				IsButton2Press())
			{
				// Leave the loop
				break;
			}

		}

		SetValveStatus(portNumber, LOW);
	}


	// ============================================================================
	void SetValveStatus(
		uint8_t channelNumber,
		bool state)
	{
		switch(channelNumber)
		{
			case 1:
				digitalWrite(PIN_VALVE_1, state);
				break;

			case 2:
				digitalWrite(PIN_VALVE_2, state);
				break;

			case 3:
				digitalWrite(PIN_VALVE_3, state);
				break;

			case 4:
				digitalWrite(PIN_VALVE_4, state);
				break;

			case 5:
				digitalWrite(PIN_VALVE_5, state);
				break;

			case 6:
				digitalWrite(PIN_PUMP, state);
				break;
		}
	}





#endif