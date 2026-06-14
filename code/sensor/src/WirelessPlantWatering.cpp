

#include <Arduino.h>

#include "wpw_Config.h"

#include "wpw_Battery.h"
#include "wpw_Blinker.h"
#include "wpw_EEPROM.h"
#include "wpw_RXTX.h"
#include "wpw_Sensor.h"
#include "wpw_WirelessPlantWatering.h"





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


#if PULL_CONFIG_CYCLE_SECONDS > 0

	// Watchdog loops between periodic config pulls, derived from the configured
	// cycle (same seconds->loops idiom as _watchdog_loop_counter above).
	const uint16_t	_config_pull_loops			= PULL_CONFIG_CYCLE_SECONDS * LOOPS_PER_MINUTE / 60;

	// Loops elapsed since the last config pull. The boot-time fetch in setup()
	// counts as the most recent pull, so we start the clock at zero.
	uint16_t		_config_pull_elapsed_loops	= 0;

#endif



// ============================================================================
uint16_t * GetWatchdogLoopPointer()
{
	return &_watchdog_loops;
}






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

}



// ============================================================================
// ============================================================================
// ============================================================================
void loop()
{

	while(true)
	{

		if (_watchdog_loop_counter == 0)
		{
			ReadBattery();
			ReadSensor();
			RadioPowerUp();
			HandleTransmitter();

			#if PULL_CONFIG_CYCLE_SECONDS > 0

				// Ride this measurement's radio-on window for a periodic config
				// pull -- no extra power-up. Only when the measurement actually
				// reached the master (a failed link would just fail the pull too).
				if (GetTxStatus() != TX_FAILURE)
				{
					// Pull on the first measurement at/after the cycle has
					// elapsed. Comparing the *remaining* loops (rather than
					// accumulating past the threshold) keeps the counter < the
					// threshold, so the uint16_t sum can never overflow.
					if (_config_pull_loops - _config_pull_elapsed_loops <= _watchdog_loops)
					{
						// Settings-only, silent pull; persist silently if changed.
						if (RequestConfiguration(true))
						{
							SaveSettingsToEeprom(false);
						}

						_config_pull_elapsed_loops = 0;
					}
					else
					{
						_config_pull_elapsed_loops += _watchdog_loops;
					}
				}

			#endif

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

		_watchdog_loop_counter--;

	}



}



