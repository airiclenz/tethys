

#include <bitOps.h>

#include <wpw_Config.h>

#include <wpw_Blinker.h>



#ifdef RX


	uint8_t     _statusBlink             = 0;
	uint8_t     _blinkArrayPos           = 0;
	uint8_t     _blinksInArray           = 0;
	uint32_t    _lastBlinkAction         = 0;

	Blink 		_blinks[BLINK_ARRAY_LENGHT];



	// ============================================================================
	void HandleBlinks()
	{

		if (_statusBlink == BLINK_INACTIVE &&
			(_blinksInArray > 0))
		{
			_statusBlink = BLINK_ACTIVE;
			digitalWrite(PIN_LED, HIGH);
			_lastBlinkAction = millis();
		}

		else if (isBit(_statusBlink, BLINK_ACTIVE))
		{
			if (millis() >= (_lastBlinkAction + _blinks[_blinkArrayPos].BlinkDuration))
			{
				_statusBlink = BLINK_POST;
				digitalWrite(PIN_LED, LOW);
				_lastBlinkAction = millis();
			}
		}

		else if (_statusBlink == BLINK_POST)
		{
			if (millis() >= (_lastBlinkAction + _blinks[_blinkArrayPos].BlinkPostDuration))
			{

				digitalWrite(PIN_LED, LOW);

				_blinksInArray--;
				_blinkArrayPos++;

				if (_blinkArrayPos >= BLINK_ARRAY_LENGHT)
				{
					_blinkArrayPos = 0;
				}

				_statusBlink = BLINK_INACTIVE;
				_lastBlinkAction = millis();
			}
		}

	}



	// =============================================================================
	void AddBlinkToQueue(
		uint16_t highTime,
		uint16_t postTime)
	{

		if (_blinksInArray < BLINK_ARRAY_LENGHT)
		{
			uint8_t newBlinkAddress =
				_blinkArrayPos +
				_blinksInArray;

			if (newBlinkAddress >= BLINK_ARRAY_LENGHT)
			{
				newBlinkAddress -= BLINK_ARRAY_LENGHT;
			}

			_blinks[newBlinkAddress].BlinkDuration = highTime;
			_blinks[newBlinkAddress].BlinkPostDuration = postTime;
			_blinksInArray++;

		}

	}



	// =============================================================================
	bool HasBlinksQueued(void)
	{
		return
			_blinksInArray > 0 ||
			_statusBlink != 0;
	}




#endif


// =============================================================================
void DoSimpleBlink(
	uint16_t highTime,
	uint16_t postTime)
{

	digitalWrite(PIN_LED, HIGH);
	delay(highTime);
	digitalWrite(PIN_LED, LOW);
	delay(postTime);

}



// =============================================================================
// Drives PIN_LED at a fixed brightness (duty = onUs/1000) for holdMs by
// bit-banging a ~1 kHz PWM waveform -- fast enough that the eye integrates it
// into a steady level instead of seeing flicker.
static void SoftPwmHold(
	uint16_t onUs,
	uint16_t holdMs)
{
	const uint16_t PERIOD_US = 1000;					// 1 kHz -> flicker-free
	uint16_t offUs = PERIOD_US - onUs;

	uint16_t cycles = ((uint32_t)holdMs * 1000) / PERIOD_US;
	if (cycles == 0)
	{
		cycles = 1;
	}

	for (uint16_t c = 0; c < cycles; c++)
	{
		if (onUs > 0)
		{
			digitalWrite(PIN_LED, HIGH);
			delayMicroseconds(onUs);
		}
		if (offUs > 0)
		{
			digitalWrite(PIN_LED, LOW);
			delayMicroseconds(offUs);
		}
	}
}



// =============================================================================
// Soft "breathing" pulse: ramps the LED brightness up and back down over about
// durationMs. PIN_LED has no usable hardware PWM here (Timer0 is repurposed for
// the sensor excitation clock), so brightness is emulated in software with the
// 1 kHz bit-banged PWM above. The duty cycle follows a quadratic (gamma) curve
// so the fade looks linear to the eye rather than snapping bright early.
void DoSoftPulse(
	uint16_t durationMs)
{
	const uint8_t  LEVELS    = 100;						// brightness steps each way
	const uint16_t PERIOD_US = 1000;
	const uint16_t stepMs    = (durationMs / 2) / LEVELS;

	// triangle sweep: 0 -> LEVELS (ramp up) -> 0 (ramp down)
	for (int16_t i = 0; i <= (2 * LEVELS); i++)
	{
		uint8_t step = (i <= LEVELS) ? (uint8_t)i : (uint8_t)(2 * LEVELS - i);

		uint16_t onUs =
			((uint32_t)PERIOD_US * step * step) / ((uint32_t)LEVELS * LEVELS);

		SoftPwmHold(onUs, stepMs);
	}

	digitalWrite(PIN_LED, LOW);
}
