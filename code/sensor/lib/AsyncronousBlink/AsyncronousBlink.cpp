/*

    (c) 2020 Airic Lenz

   See www.airiclenz.com for more information

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

 */




#include "Arduino.h"
#include "AsyncronousBlink.h"





// ============================================================================
AsyncronousBlink::AsyncronousBlink(
	uint8_t pin)
{

	_pinNumber     		= pin;

	_statusBlink   		= BLINK_INACTIVE;
	_blinkArrayPos   	= 0;
	_blinksInArray   	= 0;
	_lastBlinkAction  	= 0;
	_pinNumber    		= pin;

}



// ============================================================================
void AsyncronousBlink::Process(void)
{

	if (_statusBlink == BLINK_INACTIVE &&
	    (_blinksInArray > 0))
	{
		_statusBlink = BLINK_ACTIVE;
		digitalWrite(_pinNumber, HIGH);
		_lastBlinkAction = millis();
	}

	else if (isBit(_statusBlink, BLINK_ACTIVE))
	{
		if (millis() >= (_lastBlinkAction + _blinks[BLINK_ARRAY_LENGHT].BlinkDuration))
		{
			_statusBlink = BLINK_POST;
			digitalWrite(_pinNumber, LOW);
			_lastBlinkAction = millis();
		}
	}

	else if (_statusBlink == BLINK_POST)
	{
		if (millis() >= (_lastBlinkAction + _blinks[_blinkArrayPos].BlinkPostDuration))
		{

			digitalWrite(_pinNumber, LOW);

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
void AsyncronousBlink::AddBlinkToQueue(
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
bool AsyncronousBlink::HasBlinksQueued(void)
{
	return
		_blinksInArray > 0 ||
		_statusBlink != 0;
}



// =============================================================================
void AsyncronousBlink::SynchronousSimpleBlink(
	uint16_t highTime,
	uint16_t postTime)
{

	digitalWrite(_pinNumber, HIGH);
	delay(highTime);
	digitalWrite(_pinNumber, LOW);
	delay(postTime);

}
