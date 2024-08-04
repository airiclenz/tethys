

//#include <avr/io.h>
//#include <Arduino.h>
#include <bitOps.h>

#include "wpw_Config.h"

#include "wpw_Sensor.h"
#include "wpw_Blinker.h"



#ifdef TX


	CalibrationData _calibration =
	{
		650,	// min
		850		// max
	};


	uint8_t _TCCR0A;
	uint8_t _TCCR0B;
	uint8_t _OCR0A;

	uint16_t _sensorValue;


	// =============================================================================
	void InitializeSensor()
	{
		// safe the original states

		_TCCR0A = TCCR0A;	// 3 =	WGM01, WGM00 =	Fast PWM
		_TCCR0B = TCCR0B;	// 3 =	CS01, CS00   =	prescaler 64
		_OCR0A = OCR0A;		// 0 =

		// CLOCK
        // make PORTB Bit 2 an output (PB2, Digital 2)
		DDRB 	|= (1 << PIN_SENSOR_CLOCK);
		PORTA 	&= ~(1 << PIN_SENSOR_CLOCK);

		// SENSOR READ
		// make PORTA Bit 3 an input (PA3, Digital 7) --> Bit LOW

		DDRA 	&= ~(1 << PIN_SENSOR_READ);
		PORTA 	&= ~(1 << PIN_SENSOR_READ);

	}




	// =============================================================================
	void EnableSensorClock0Pin2()
	{

		// BIT		| 7      | 6      | 5     | 4      | 3      | 2      | 1      | 0      |
		// TCCR0A   | COM0A1 | COM0A0 |COM0B1 | COM0B0 | –      | –      | WGM01  | WGM00  |
		// TCCR0B   | FOC0A  | FOC0B  | –     | -      | WGM02  | CS02   | CS01   | CS00   |


		DDRB 	|= (1 << PIN_SENSOR_CLOCK);

		TCNT0 = 0;

		OCR0A = 0;

		TCCR0B =
			(1 << WGM02) |		// PWM, Phase Correct, OCRA
			(1 << CS01);		// Prescaler 8 ((Mhz clock with duty 50% --> 4Mhz / 8 = 500kHz))

		TCCR0A =
			(1 << COM0A0) | 	// Toggle OC0A on Compare Match (OC0A --> PB2, Digital 2)
			(1 << WGM00);  		// PWM, Phase Correct, OCRA

	}


	// =============================================================================
	void DisableSensorClock0Pin2()
	{

		TCCR0A = 	_TCCR0A;
		TCCR0B = 	_TCCR0B;
		OCR0A = 	_OCR0A;

		// set the clock pin to low
		PORTA 	&= ~(1 << PIN_SENSOR_CLOCK);

	}




    // ============================================================================
    uint16_t ReadSensor()
    {
		//digitalWrite(PIN_LED, HIGH);

        EnableSensorClock0Pin2();

		// the system timing is changed when the PWM is on
		// as it uses timer 0 (running at about 153% fast)
		// the value below is reflecting about 65ms

		delay(200);

		DisableSensorClock0Pin2();

		_sensorValue = analogRead(PIN_SENSOR_READ);

		//digitalWrite(PIN_LED, LOW);

        return _sensorValue;
    }



	// ============================================================================
	uint8_t GetMoistureLevelPercent()
	{
		int16_t value =
			map(
				_sensorValue,
				_calibration.MinimumValue,
				_calibration.MaximumValue,
				0,
				100);

		// invert as lowets value = highest moisture
		value = 100 - value; 

		if (value < 0)
		{
			return 0;
		}

		if (value > 100)
		{
			return 100;
		}

		return value;
	}


	// ============================================================================
	uint16_t DoCalibrationMeasurement()
	{
		for (uint8_t i=0; i<10; i++)
		{
			DoSimpleBlink(300, 200);
		}

		for (uint8_t i=0; i<20; i++)
		{
			DoSimpleBlink(100,100);
		}

		DoSimpleBlink(1000, 0);

		return ReadSensor();

	}


	// ============================================================================
	void Calibrate()
	{
		// First Measurement
		uint16_t value1 = DoCalibrationMeasurement();

		delay(1000);

		// Second Measurement
		uint16_t value2 = DoCalibrationMeasurement();

		if (value1 < value2)
		{
			_calibration.MinimumValue = value1;
			_calibration.MaximumValue = value2;
		}
		else
		{
			_calibration.MinimumValue = value2;
			_calibration.MaximumValue = value1;
		}

	}



	// =============================================================================
	CalibrationData * GetCalibrationPointer()
	{
		return &_calibration;
	}


#endif



#ifdef RX

	// Status, TriggerLevel, MeasureFrequency, PumpDuration, TransmissionPower
	// Moisture %, Moisture, Timestamp, PackageCount, PumpCount, Battery Voltage

	Sensor _sensors[SENSOR_COUNT] =
	{
		{ CHANNEL_ENABLED, MoistureLevel::Dry, 120, 10, RF24_PA_LOW, 0, 0, 0, 0, 0, 0.0 },
		{ CHANNEL_ENABLED, MoistureLevel::Dry, 120, 10, RF24_PA_LOW, 0, 0, 0, 0, 0, 0.0 },
		{ CHANNEL_ENABLED, MoistureLevel::Dry, 120, 10, RF24_PA_LOW, 0, 0, 0, 0, 0, 0.0 },
		{ CHANNEL_ENABLED, MoistureLevel::Dry, 120, 10, RF24_PA_LOW, 0, 0, 0, 0, 0, 0.0 },
		{ CHANNEL_ENABLED, MoistureLevel::Dry, 120, 10, RF24_PA_LOW, 0, 0, 0, 0, 0, 0.0 }
	};




	// ============================================================================
	Sensor * GetSensorPointer(uint8_t index)
	{
		return &_sensors[index];
	}


	// ============================================================================
	uint8_t GetMoistureLevelFromPercent(
		uint8_t percentValue,
		bool doBias)
	{
		uint8_t rawMoisture = 
			1 + ((float)percentValue / 20.2f);
		
		if (doBias)
		{
			// bias is TODO
			return rawMoisture;
		}
		else
		{
			return rawMoisture;
		}
	}




#endif