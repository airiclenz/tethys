

#include <bitOps.h>

#include "wpw_Config.h"

#include "wpw_Blinker.h"
#include "wpw_UI.h"
#include "wpw_Input.h"


#ifdef RX


    uint8_t 	_statusInput            	= 0;
	uint8_t		_statusAcceleration			= 0;

    uint32_t    _lastButtonEvent    		= 0;
	uint16_t	_waterReadValue					= 0;
	float		_accelerationFactor			= 0;

	bool		_waterIsOk					= false;
	bool 		_useWaterSensor				= true;


	// =============================================================================
	bool * GetUseWaterSensorPointer()
	{
		return &_useWaterSensor;
	}


	// =============================================================================
	void InterruptButton1()
	{
		
		if (isBit(_statusInput, SINGLEPRESS_POSTDELAY))
		{
			return;
		}
		
		
		bool stateButton1 = !digitalRead(PIN_BUTTON_1);

		if (stateButton1)
		{
			setBit(_statusInput, B1_DOWN);

			if (isBit(_statusInput, B2_DOWN))
			{
				setBit(_statusInput, DOUBLE_DOWN);
			}
		}
		else
		{

			if(isBit(_statusInput, DOUBLE_DOWN))
			{
				setBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);

				deleteBit(_statusInput, SINGLEREAD_B1_PRESSED);
				deleteBit(_statusInput, SINGLEREAD_B2_PRESSED);
			}


			else if (!isBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED))
			{
				setBit(_statusInput, SINGLEREAD_B1_PRESSED);

				deleteBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);
				deleteBit(_statusInput, SINGLEREAD_B2_PRESSED);
			}


			deleteBit(_statusInput, B1_DOWN);
			deleteBit(_statusInput, DOUBLE_DOWN);

			deleteBit(_statusAcceleration, ACCELERATION_PHASE);
			deleteBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY);

			RegisterDisplayRefresh();
		}

		_lastButtonEvent = millis();
	}


	// =============================================================================
	void InterruptButton2()
	{

		if (isBit(_statusInput, SINGLEPRESS_POSTDELAY))
		{
			return;
		}
		
		
		bool stateButton2 = !digitalRead(PIN_BUTTON_2);

		if (stateButton2)
		{
			setBit(_statusInput, B2_DOWN);

			if (isBit(_statusInput, B1_DOWN))
			{
				setBit(_statusInput, DOUBLE_DOWN);
			}
		}
		else
		{

			if(isBit(_statusInput, DOUBLE_DOWN))
			{
				setBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);

				deleteBit(_statusInput, SINGLEREAD_B1_PRESSED);
				deleteBit(_statusInput, SINGLEREAD_B2_PRESSED);
			}


			else if (!isBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED))
			{
				setBit(_statusInput, SINGLEREAD_B2_PRESSED);

				deleteBit(_statusInput, SINGLEREAD_B1_PRESSED);
				deleteBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);
			}


			deleteBit(_statusInput, B2_DOWN);
			deleteBit(_statusInput, DOUBLE_DOWN);

			deleteBit(_statusAcceleration, ACCELERATION_PHASE);
			deleteBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY);

			RegisterDisplayRefresh();
		}

		_lastButtonEvent = millis();
	}


	// =============================================================================
    void HandleInput()
    {

		// -----------------------------
		// Handle the delay after a double press to avoid registering
		// actions that we don't want. This is needed as actions are regitered
		// on KeyUp and thus an extra key event would be regitered after the
		// first of the two buttons would be released.
		if (isBit(_statusInput, DOUBLEPRESS_POSTDELAY))
		{
			if (millis() > _lastButtonEvent + DOUBLE_PRESS_POSTDELAY_DURATION)
			{
				deleteBit(_statusInput, DOUBLEPRESS_POSTDELAY);

				deleteBit(_statusInput, SINGLEREAD_B1_PRESSED);
				deleteBit(_statusInput, SINGLEREAD_B2_PRESSED);
				deleteBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);
			}
		}

		if (isBit(_statusInput, SINGLEPRESS_POSTDELAY))
		{
			if (millis() > _lastButtonEvent + DEBOUNCE_DELAY_DURATION)
			{
				deleteBit(_statusInput, SINGLEPRESS_POSTDELAY);
			}
		}

	}


	// =============================================================================
	int8_t HandleJog()
	{

		// -----------------------------
		// are we in the initial acceleration delayand should
		// end it?
		if (isBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY))
		{
			if (millis() > _lastButtonEvent + ACCELERATION_DELAY_DURATION)
			{
				if (isBit(_statusInput, B1_DOWN) ||
					isBit(_statusInput, B2_DOWN))
				{
					setBit(_statusAcceleration, ACCELERATION_PHASE);
					_accelerationFactor = ACCELERATION_START_FACTOR;
				}

				deleteBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY);
			}

			else
			{
				return 0;
			}
		}



		// -----------------------------
		// in Acceleration phase
		if (!isBit(_statusInput, DOUBLE_DOWN))
		{
			if (isBit(_statusAcceleration, ACCELERATION_PHASE))
			{

				if (_accelerationFactor < ACCELERATION_LIMIT)
				{
					_accelerationFactor *= _accelerationFactor;
				}


				if (isBit(_statusInput, B1_DOWN))
				{
					return (int8_t)_accelerationFactor;
				}

				if (isBit(_statusInput, B2_DOWN))
				{
					return -(int8_t)_accelerationFactor;
				}

			}
			else
			{
				if (isBit(_statusInput, B1_DOWN))
				{
					setBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY);
					return 0;
				}

				if (isBit(_statusInput, B2_DOWN))
				{
					setBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY);
					return 0;
				}
			}
		}
		// DOUBLE_DOWN:
		else
		{
			deleteBit(_statusAcceleration, ACCELERATION_PHASE);
			deleteBit(_statusAcceleration, ACCELERATION_INITIAL_DELAY);
			return 0;
		}


		if (IsButton1Press())
		{
			return 1;
		}

		if (IsButton2Press())
		{
			return -1;
		}

		return 0;
	}




	// =============================================================================
	void DeleteSingleReadFlags()
	{
		deleteBit(_statusInput, SINGLEREAD_B1_PRESSED);
		deleteBit(_statusInput, SINGLEREAD_B2_PRESSED);
		deleteBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);
	}




	// =============================================================================
	bool IsButton1Press()
	{
		if (isBit(_statusInput, SINGLEREAD_B1_PRESSED) &&
			!isBit(_statusInput, DOUBLEPRESS_POSTDELAY))
		{
			deleteBit(_statusInput, SINGLEREAD_B1_PRESSED);
			setBit(_statusInput, SINGLEPRESS_POSTDELAY);
			
			AddBlinkToQueue(10, 20);
			RegisterDisplayRefresh();

			return true;
		}
		else
		{
			return false;
		}
	}


	// =============================================================================
	bool IsButton2Press()
	{
		if (isBit(_statusInput, SINGLEREAD_B2_PRESSED) &&
			!isBit(_statusInput, DOUBLEPRESS_POSTDELAY))
		{
			deleteBit(_statusInput, SINGLEREAD_B2_PRESSED);
			setBit(_statusInput, SINGLEPRESS_POSTDELAY);
			
			AddBlinkToQueue(10, 20);
			RegisterDisplayRefresh();

			return true;
		}
		else
		{
			return false;
		}
	}


	// =============================================================================
	bool IsDoublePress()
	{
		if (isBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED) &&
			!isBit(_statusInput, DOUBLEPRESS_POSTDELAY))
		{
			deleteBit(_statusInput, SINGLEREAD_DOUBLE_PRESSED);
			setBit(_statusInput, DOUBLEPRESS_POSTDELAY);

			AddBlinkToQueue(30, 50);
			AddBlinkToQueue(30, 20);
			RegisterDisplayRefresh();

			return true;
		}
		else
		{
			return false;
		}

	}



	// =============================================================================
	void ActivateJogging()
	{
		_statusAcceleration = 0;
		setBit(_statusAcceleration, ACCELERATION_ENABLED);

	}


	// =============================================================================
	void DeactivateJogging()
	{
		_statusAcceleration = 0;
	}


    // =============================================================================
    bool IsWaterOk()
    {
        return _waterIsOk;
    }


	// =============================================================================
    uint16_t GetWaterReadout()
    {
        return _waterReadValue;
    }


    // =============================================================================
    bool ReadWaterSensor()
    {
        // charge the capacitor
        pinMode(PIN_WATER,  OUTPUT);
        digitalWrite(PIN_WATER, HIGH);
        delayMicroseconds(250);

        // switch the pin to read mode
        digitalWrite(PIN_WATER, LOW);
        pinMode(PIN_WATER,  INPUT);

        // wait for the capacitor to discharge through the water
        delay(30);

        // read the analog value
		_waterReadValue = analogRead(PIN_WATER);

		// return if it is still charged (no water = read HIGH)
        if (_waterReadValue > 512)
        {
            _waterIsOk = false;
        }
        else
        {
            _waterIsOk = true;
        }

		digitalWrite(PIN_WATER, LOW);
        return _waterIsOk;

    }

#endif