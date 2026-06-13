

#ifndef wpw_RXTX

    #define wpw_RXTX

    #include <Arduino.h>
    #include "wpw_Sensor.h"


    #define     TX_INACTIVE         B00000000
    #define     TX_ACTIVE           B00000001
    #define     TX_FAILURE          B00000010


    #define     DATATYPE_SENSORDATA     			0
	#define		DATATYPE_SENSORDATA_BATTERYALERT	1

	// MASTER --> SENSOR:	Trigger Calibration
	#define		DATATYPE_CMD_CALIBRATE				5

	// SENSOR --> MASTER: 	Request the Configuration
	#define		DATATYPE_CMD_GETCONFIG				6
	#define		DATATYPE_CONFIG						7



	// Wire structs are sent/received as raw bytes, so the layout MUST match the
	// master's struct format strings in code/master/core/protocol.py exactly.
	// packed -> no padding (the master assumes a tight little-endian layout);
	// the static_asserts below fail the build if the size ever drifts.

	// Master --> Sensor   (matches Python "<BBHB?")
	struct __attribute__((packed)) ConfigurationPackage
	{
		uint8_t		ProtocolVersion;
		uint8_t     PackageType;
		uint16_t    MeasureFrequency;
		uint8_t		TransmissionPowerLevel;
		bool        TriggerCalibration;
	};

	// Sensor --> Master   (matches Python "<BBBf")
	struct __attribute__((packed)) Package
	{
		uint8_t		ProtocolVersion;
		uint8_t     PackageType;
		uint8_t   	MoistureLevel;
		float       BatteryVoltage;
	};

	static_assert(sizeof(ConfigurationPackage) == 6,
		"ConfigurationPackage must be 6 packed bytes (matches master <BBHB?)");
	static_assert(sizeof(Package) == 7,
		"Package must be 7 packed bytes (matches master <BBBf)");




    void InitializeRadio(void);
    uint8_t * GetTransmissionPowerPointer(void);
    void SetTransmissionPower(void);


    #ifdef RX

        void SetupRadioForRx(void);
        void HandleReceiver();
		bool SendConfiguration(uint16_t, bool);

    #endif

    #ifdef TX

        uint8_t GetTxStatus(void);


        void RadioPowerUp(void);
        void RadioPowerDown(void);

        void SetupRadioForTx();
        void HandleTransmitter(void);
		bool RequestConfiguration(void);

    #endif




#endif