

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

	// Start the down-counter at the settle window so the first measurement is
	// deferred ~STARTUP_SETTLE_SECONDS after boot (the node sleeps through it via
	// the normal loop/Sleep cycle; each loop is ~9 s, so the value rounds down to a
	// whole loop count). After the first capture the counter is reloaded with the
	// configured measure interval, so this only affects the first reading.
	uint16_t    _watchdog_loop_counter		= STARTUP_SETTLE_SECONDS * LOOPS_PER_MINUTE / 60;



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

		// Ask the master for fresh config, but don't camp here draining the
		// battery if it never answers (it may be busy, or this is a first-ever
		// boot with no master in range). A handful of bounded retries with
		// linear backoff, then fall back to the settings already loaded from
		// EEPROM and start measuring. The master answers from its config cache,
		// so a reachable master replies on the first attempt.
		const uint8_t	MAX_CONFIG_RETRIES = 5;
		bool			success            = false;

		for (uint8_t attempt = 0; !success && attempt < MAX_CONFIG_RETRIES; attempt++)
		{
			success = RequestConfiguration();

			if (!success)
			{
				// linear backoff between attempts: 1s, 2s, 3s, ...
				delay((uint32_t)(attempt + 1) * 1000);
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

					// Four short flashes: extends the radio-status family
					// (1 = config ok, 2 = no reply, 3 = bad frame, 4 = send failed).
					DoSimpleBlink(15, 150);
					DoSimpleBlink(15, 150);
					DoSimpleBlink(15, 150);
					DoSimpleBlink(15, 0);
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



