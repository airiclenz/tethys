

#ifndef wpw_Sensor

    #define wpw_Sensor

    #include <Arduino.h>



	#define 	SENSOR_COUNT			5

	#define		CHANNEL_ENABLED			BIT_0
	#define		CHANNEL_TYPE_ISVALVE	BIT_1
	#define		CHANNEL_CALIBRATE		BIT_2
	#define		CHANNEL_BATTERY_ALERT	BIT_3
	#define		CHANNEL_CHECK_PUMP		BIT_4



	struct MoistureLevel
	{
		static const uint8_t	Wet 	= 5;
		static const uint8_t	Moist 	= 4;
		static const uint8_t	Medium	= 3;
		static const uint8_t	Dry 	= 2;
		static const uint8_t	Dusty 	= 1;
	};


	struct CalibrationData
	{
		uint16_t	MinimumValue;
		uint16_t	MaximumValue;
	};


    struct Sensor
    {
			// Settings
			uint8_t		Status;
			uint8_t		TriggerLevel;
			uint16_t 	MeasureFrequency;
			uint16_t 	PumpDuration;
			uint8_t		TransmissionPower;

			// Sensor Data
			uint8_t    	MoistureLevelPercent;
			uint8_t		MoistureLevel;
			uint32_t    Timestamp;
			uint16_t    PackageCount;
			uint16_t    PumpCount;
			float       BatteryVoltage;
	};



	void InitializeSensor(void);


	void EnableSensorClock0Pin2(void);
	void DisableSensorClock0Pin2(void);

	uint16_t ReadSensor(void);
	uint8_t GetMoistureLevel(void);
	uint8_t GetMoistureLevelPercent(void);
	CalibrationData * GetCalibrationPointer(void);

	void Calibrate(void);




#endif