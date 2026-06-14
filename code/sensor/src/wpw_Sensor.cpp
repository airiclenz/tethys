

//#include <avr/io.h>
//#include <Arduino.h>
#include <bitOps.h>

#include <util/delay.h>

#include "wpw_Config.h"

#include "wpw_Sensor.h"
#include "wpw_Blinker.h"
#include "wpw_Battery.h"



#ifdef TX


	// NOTE: these are placeholder defaults only. They are overwritten from EEPROM
	// at boot and should be re-measured with Calibrate() after flashing, because
	// the excitation/normalisation below changes the raw scale relative to older
	// firmware. They merely need to form a valid (non-degenerate) span so the
	// first conversion before any calibration cannot divide by zero.
	CalibrationData _calibration =
	{
		650,	// min raw (wettest expected -> lowest reading)
		850		// max raw (driest expected -> highest reading)
	};


	// --- Measurement tuning -----------------------------------------------------

	// Excitation window for the capacitive probe. The signal node settles with
	// tau = R6 * C7 ~= 510 kohm * 1 uF ~= 510 ms. The old delay(200) ran while
	// Timer0 was repurposed for the excitation clock (see ReadSensor), so it was
	// really only ~50 ms -> the node charged to a small fraction of full scale,
	// giving a tiny dry/wet swing that clipped at the ends. Excite for >~1 tau to
	// open up the usable range. Tune on hardware.
	#define SENSOR_EXCITATION_MS		750

	// Number of ADC conversions averaged per measurement (one extra is discarded
	// first). Reduces single-sample noise from the high-impedance node next to
	// the radio.
	#define SENSOR_SAMPLE_COUNT			16

	// Readings are normalised to this nominal supply. The ADC is ratiometric to
	// VCC but the sensor signal's diode drop is not, so a sagging battery drifts
	// the raw value at constant moisture. Scaling by the measured VCC removes that
	// drift while keeping the value on the familiar 0..1023 scale.
	#define SENSOR_VCC_NOMINAL_MV		3300

	// Smallest dry/wet span (in normalised counts) accepted by Calibrate(). Below
	// this the calibration is all-or-nothing and map() could divide by ~zero.
	#define SENSOR_MIN_CALIBRATION_SPAN	40


	uint8_t _TCCR0A;
	uint8_t _TCCR0B;
	uint8_t _OCR0A;
	uint8_t _TIMSK0;

	uint16_t _sensorValue;


	// =============================================================================
	void InitializeSensor()
	{
		// safe the original states

		_TCCR0A = TCCR0A;	// 3 =	WGM01, WGM00 =	Fast PWM
		_TCCR0B = TCCR0B;	// 3 =	CS01, CS00   =	prescaler 64
		_OCR0A = OCR0A;		// 0 =
		_TIMSK0 = TIMSK0;	// Timer0 interrupt mask (TOIE0 drives millis())

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


		// Detach Timer0's interrupts BEFORE reconfiguring it. On this ATtiny84
		// core Timer0 also drives millis(); the PWM mode below (OCR0A = 0) makes
		// TOV0 set continuously, so a still-enabled TIMER0_OVF ISR would fire
		// back-to-back and starve the foreground _delay_ms() excitation busy-wait
		// in ReadSensor() -> the node freezes. Restored in DisableSensorClock0Pin2().
		TIMSK0 &= ~((1 << TOIE0) | (1 << OCIE0A) | (1 << OCIE0B));

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

		// re-attach Timer0's interrupts (restores millis()); a single pending
		// TOV0 may fire one harmless extra tick.
		TIMSK0 = 	_TIMSK0;

		// set the clock pin to low
		PORTA 	&= ~(1 << PIN_SENSOR_CLOCK);

	}




    // ============================================================================
	// Averages several ADC conversions on the sensor pin. ReadBattery() leaves
	// ADMUX pointing at the internal 1.1V bandgap (MUX5 set); analogRead()
	// reprograms it for PA3/VCC, but the first conversion after a channel change
	// is unreliable, so it is taken and discarded before averaging.
	uint16_t ReadSensorRawAveraged()
	{
		(void) analogRead(PIN_SENSOR_READ);		// discard first conversion after channel change

		uint32_t sum = 0;
		for (uint8_t i = 0; i < SENSOR_SAMPLE_COUNT; i++)
		{
			sum += analogRead(PIN_SENSOR_READ);
		}

		return (uint16_t)(sum / SENSOR_SAMPLE_COUNT);
	}


	// ============================================================================
	// Normalises a raw 10-bit reading to a fixed nominal supply voltage so that a
	// sagging battery does not drift the result at constant moisture. Uses the VCC
	// measured by the most recent ReadBattery(); falls back to the raw value if
	// VCC is not yet known.
	uint16_t NormaliseToNominalVcc(uint16_t rawValue)
	{
		uint16_t vccMilliVolts = (uint16_t)(GetBatteryVoltage() * 1000.0f);

		// Fall back to the raw value if VCC is not yet known / implausibly low.
		// A real supply reads ~2500..4200 mV; an un-measured battery reports only
		// BATTERY_CALIBRATION_OFFSET (~20 mV), which would otherwise crush every
		// reading to ~zero.
		if (vccMilliVolts < 1000)
		{
			return rawValue;
		}

		return (uint16_t)(((uint32_t)rawValue * vccMilliVolts) / SENSOR_VCC_NOMINAL_MV);
	}


    // ============================================================================
    uint16_t ReadSensor()
    {
		//digitalWrite(PIN_LED, HIGH);

        EnableSensorClock0Pin2();

		// Timer0 is repurposed as the 500 kHz excitation clock above, so the
		// Arduino delay()/millis() time base is invalid here (it would run several
		// times too fast). Use the cycle-counting busy-wait from <util/delay.h>
		// instead: it is derived from F_CPU and scales together with the excitation
		// frequency, so the number of charge pulses delivered to the sensor stays
		// constant even as the internal RC oscillator drifts with temperature and
		// supply voltage.
		for (uint16_t i = 0; i < SENSOR_EXCITATION_MS; i++)
		{
			_delay_ms(1);
		}

		// Sample WHILE the node is still excited, at a deterministic point. (The
		// old code read after disabling the clock, while C7 was already
		// discharging through R5 at an undefined instruction-timing offset.)
		uint16_t raw = ReadSensorRawAveraged();

		DisableSensorClock0Pin2();

		_sensorValue = NormaliseToNominalVcc(raw);

		//digitalWrite(PIN_LED, LOW);

        return _sensorValue;
    }



	// ============================================================================
	uint8_t GetMoistureLevelPercent()
	{
		// Guard against a degenerate calibration (equal endpoints) which would
		// make map() divide by zero.
		if (_calibration.MaximumValue <= _calibration.MinimumValue)
		{
			return 0;
		}

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
		// Boot calibration runs before loop() ever calls ReadBattery(), so take a
		// fresh supply reading here -- otherwise NormaliseToNominalVcc() has no
		// valid VCC and the measurements collapse toward zero.
		ReadBattery();

		// First Measurement
		uint16_t value1 = DoCalibrationMeasurement();

		delay(1000);

		// Second Measurement
		uint16_t value2 = DoCalibrationMeasurement();

		uint16_t newMin = (value1 < value2) ? value1 : value2;
		uint16_t newMax = (value1 < value2) ? value2 : value1;

		// Reject a calibration whose dry/wet endpoints are too close together: the
		// resulting range would be all-or-nothing and map() could divide by ~zero.
		// Keep the previous calibration and signal the rejection with a long blink.
		if ((newMax - newMin) < SENSOR_MIN_CALIBRATION_SPAN)
		{
			DoSimpleBlink(2000, 0);
			return;
		}

		_calibration.MinimumValue = newMin;
		_calibration.MaximumValue = newMax;

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