/*

    (c) 2020 Airic Lenz

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


#ifndef AsyncronousBlink_h
#define AsyncronousBlink_h


#include "Arduino.h"
#include "bitOps.h"



#define     BLINK_INACTIVE          B00000000
#define     BLINK_ACTIVE            B00000001
#define     BLINK_POST              B00000010

#define		BLINK_ARRAY_LENGHT		5


// ============================================================================
// ============================================================================
// ============================================================================
class AsyncronousBlink {

	///////////////////////////////////////////
	public:
	///////////////////////////////////////////

		AsyncronousBlink(uint8_t);

		void Process(void);
		void AddBlinkToQueue(uint16_t, uint16_t);
		bool HasBlinksQueued(void);
		void SynchronousSimpleBlink(uint16_t, uint16_t);


	///////////////////////////////////////////
	private:
	///////////////////////////////////////////

		struct Blink
		{
			uint16_t BlinkDuration;
			uint16_t BlinkPostDuration;
		};


		uint8_t     _statusBlink;
		uint8_t     _blinkArrayPos;
		uint8_t     _blinksInArray;
		uint32_t    _lastBlinkAction;
		uint8_t		_pinNumber;

		Blink 		_blinks[BLINK_ARRAY_LENGHT];

};

#endif
