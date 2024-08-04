

#include <bitOps.h>

#include <wpw_Config.h>

#include <wpw_Battery.h>


// https://wp.josh.com/2014/11/06/battery-fuel-guage-with-zero-parts-and-zero-pins-on-avr/
// https://gist.github.com/bigjosh/ae9ffcd9fd0da9a25807#file-nopartsbatterygauge-c


#ifdef TX


	bool _isBatteryOk = false;
	uint16_t _batteryReadOut = 0;
	float _batteryVoltage = 0;

	// ============================================================================
	void InitializeBattery()
	{
		pinMode(PIN_BATTERY, INPUT);
	}


	// ============================================================================
	bool IsBatteryOk()
	{
		return _isBatteryOk;
	}


	// ============================================================================
	float GetBatteryVoltage()
	{
		return _batteryVoltage + BATTERY_CALIBRATION_OFFSET;
	}

	// ============================================================================
	void ReadBattery()
	{
		
		// BIT		| 7      | 6      | 5      | 4      | 3      | 2      | 1      | 0      |
		// ADMUX	|REFS1   | REFS0  | MUX5   | MUX4   | MUX3   | MUX2   | MUX1   | MUX0   |
		
		// REFS0 & REFS1 = 0 --> VCC as VRef
		// MUX0 & MUX5   = 1 --> Single Ended Internal Ref (1.1V) as Vin

		ADMUX	= 	(1 << MUX5) |
					(1 << MUX0);	

		// ADEN: ADC Enable
		// ADPS1 & ADPS2: Pre-Scaler of 64 --> 8MHz / 64 = 125 kHz ADC Clock

		ADCSRA = 	(1 << ADEN) | 
					(1 << ADPS2) | 
					(1 << ADPS1);

		// After switching to internal voltage reference the ADC requires a settling time 
		// of 1ms before measurements are stable. Conversions starting before this 
		// may not be reliable. The ADC must be enabled during the settling time.
		delay(1);

		// start the conversion
		ADCSRA |= 	(1 << ADSC);
		
		// wait for the converion to finish: ADSC will read as one as long as a conversion 
		// is in progress. When the conversion is complete, it returns to zero
		while( ADCSRA & (1 << ADSC) );
		
		// After the conversion is complete (ADIF is high), the conversion result 
		// can be found in the ADC Result Registers (ADCL, ADCH).
		uint8_t low  = ADCL;
		uint8_t high = ADCH;

		_batteryReadOut = (high << 8) | low;
		
		_batteryVoltage = 1.1f / (float)_batteryReadOut * 1024;

		_isBatteryOk = (_batteryVoltage + BATTERY_CALIBRATION_OFFSET) > BATTERY_WARNING_VOLTAGE;
	}





#endif


