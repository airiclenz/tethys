

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
