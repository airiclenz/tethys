

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

	// SENSOR --> MASTER:	Periodic, settings-only config pull. Same reply as
	// DATATYPE_CONFIG, but the master answers without the calibration trigger
	// and never clears a pending calibration flag -- calibration stays a
	// boot-only operation requested via DATATYPE_CMD_GETCONFIG.
	#define		DATATYPE_CMD_GETCONFIG_PERIODIC		8



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

	// Sensor --> Master, config request (boot-time DATATYPE_CMD_GETCONFIG or the
	// periodic DATATYPE_CMD_GETCONFIG_PERIODIC). Carries the firmware version
	// (VERSION.SUBVERSION.BUILDNUMBER from wpw_Version.h) where a data Package
	// carries moisture+battery -- those bytes are meaningless on a request, so
	// the master reads the version here and persists it once per boot.
	// The first two bytes match Package, so the master dispatches on PackageType
	// the same way and only this parser reads the version.   (matches Python "<BBBBB")
	struct __attribute__((packed)) ConfigRequestPackage
	{
		uint8_t		ProtocolVersion;
		uint8_t     PackageType;
		uint8_t		FirmwareVersion;
		uint8_t		FirmwareSubVersion;
		uint8_t		FirmwareBuildNumber;
	};

	static_assert(sizeof(ConfigurationPackage) == 6,
		"ConfigurationPackage must be 6 packed bytes (matches master <BBHB?)");
	static_assert(sizeof(Package) == 7,
		"Package must be 7 packed bytes (matches master <BBBf)");
	static_assert(sizeof(ConfigRequestPackage) == 5,
		"ConfigRequestPackage must be 5 packed bytes (matches master <BBBBB)");




    void InitializeRadio(void);
    uint8_t * GetTransmissionPowerPointer(void);
    void SetTransmissionPower(void);




	uint8_t GetTxStatus(void);


	void RadioPowerUp(void);
	void RadioPowerDown(void);

	void SetupRadioForTx();
	void HandleTransmitter(void);
	// periodic == true: a settings-only pull (uses the periodic opcode,
	// never triggers calibration, stays silent on the LED). Defaults to the
	// boot-time behaviour (full config, may calibrate, full LED feedback).
	bool RequestConfiguration(bool periodic = false);


#endif