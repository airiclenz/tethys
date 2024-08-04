

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



	struct ConfigurationPackage
	{
		uint8_t     PackageType;
		uint16_t    MeasureFrequency;
		uint8_t		TransmissionPowerLevel;
		bool        TriggerCalibration;
	};


	struct Package
	{
		uint8_t     PackageType;
		uint8_t   	MoistureLevel;
		float       BatteryVoltage;
	};




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