

#include <Arduino.h>

#include "wpw_Config.h"

#include "wpw_Battery.h"
#include "wpw_Blinker.h"
#include "wpw_UI.h"
#include "wpw_EEPROM.h"
#include "wpw_Input.h"
#include "wpw_Pumps.h"
#include "wpw_RXTX.h"
#include "wpw_Sensor.h"
#include "wpw_WirelessPlantWatering.h"




#ifdef TX

	// ------------------------------------------------
	// WATCHDOG / SLEEP

	// one loop ~ 9 sec --> 15min = 104.4 loops

	uint16_t	_watchdog_loops				= 60 * LOOPS_PER_MINUTE; // 60min / 1h
	uint16_t    _watchdog_loop_counter		= 0;



	// ============================================================================
	uint16_t * GetWatchdogLoopPointer()
	{
		return &_watchdog_loops;
	}


#endif




// ============================================================================
// ============================================================================
// ============================================================================
void setup()
{

	#ifdef DEBUG
		Serial.begin(57600);
	#endif

	pinMode(PIN_LED, OUTPUT);

	randomSeed(analogRead(0));

	InitializeRadio();


	// A Water Sensor
	#ifdef TX

        delay(750);

		randomSeed(analogRead(0));

        // Do some intial blinks (blink the ID),
		// to show that the device is powered
		for (uint8_t i=0; i<SENSOR_NUMBER; i++)
		{
			DoSimpleBlink(150, 300);
		}
		delay(750);

		SetupRadioForTx();
		InitializeSensor();
		InitializeSleep();
		InitializeEeprom();
		InitializeBattery();

		delay(750);

		uint32_t 	lastRequestTime = 0;
		bool 		success 		= false;
		uint16_t	retryCounter 	= 1000;


		while (!success && retryCounter != 0)
		{
			if (millis() > lastRequestTime + 1000)
			{
				retryCounter--;
                success = RequestConfiguration();
                lastRequestTime = millis();
			}
		}

		if (success || IsSettingsFlagDirty())
		{
			SaveSettingsToEeprom();
		}

		delay(100);

	#endif


	// The master unit
	#ifdef RX

		pinMode(PIN_BUTTON_1, INPUT);
		pinMode(PIN_BUTTON_2, INPUT);
		pinMode(PIN_WATER, INPUT);

		// Activate / Deactivate the internal pull-ups
		digitalWrite(PIN_BUTTON_1, HIGH);
		digitalWrite(PIN_BUTTON_2, HIGH);
		digitalWrite(PIN_WATER, LOW);


		pinMode(PIN_VALVE_1, OUTPUT);
		pinMode(PIN_VALVE_2, OUTPUT);
		pinMode(PIN_VALVE_3, OUTPUT);
		pinMode(PIN_VALVE_4, OUTPUT);
		pinMode(PIN_VALVE_5, OUTPUT);
		pinMode(PIN_PUMP, OUTPUT);

		digitalWrite(PIN_VALVE_1, LOW);
		digitalWrite(PIN_VALVE_2, LOW);
		digitalWrite(PIN_VALVE_3, LOW);
		digitalWrite(PIN_VALVE_4, LOW);
		digitalWrite(PIN_VALVE_5, LOW);
		digitalWrite(PIN_PUMP, LOW);


		attachInterrupt(
			digitalPinToInterrupt(PIN_BUTTON_1),
			InterruptButton1,
			CHANGE);

		attachInterrupt(
			digitalPinToInterrupt(PIN_BUTTON_2),
			InterruptButton2,
			CHANGE);


		InitializeDisplay();
		PaintSplashScreen();

		RegisterDisplayRefresh();

		InitializeEeprom();

		SetupRadioForRx();

		ReadWaterSensor();

	#endif

}



// ============================================================================
// ============================================================================
// ============================================================================
void loop()
{

	#ifdef TX

		while(true)
		{

			if (_watchdog_loop_counter == 0)
			{
				ReadBattery();
				ReadSensor();
				RadioPowerUp();
				HandleTransmitter();
				RadioPowerDown();


				if (GetTxStatus() == TX_FAILURE)
				{
					// loop for about 15min, then try again...
					_watchdog_loop_counter = 100; // random(5) + 1;

					DoSimpleBlink(10, 100);
				}
				else
				{
					_watchdog_loop_counter = _watchdog_loops;
				}

			}

			DoSimpleBlink(5, 0);

			Sleep();
			// delay(5000);

			_watchdog_loop_counter--;

		}

	#endif

	#ifdef RX

		while(true)
		{
			HandleReceiver();
			HandleBlinks();
			HandleInput();
			HandleBlinks();
			HandleDisplay();
			HandleBlinks();
			HandlePumpsAndValves();
			HandleBlinks();
		}


	#endif

}



