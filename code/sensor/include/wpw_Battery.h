

#ifndef wpw_Battery

    #define wpw_Battery


    #include <Arduino.h>

	#include <wpw_Config.h>


	#define 	BATTERY_CALIBRATION_OFFSET	0.02

	#define		BATTERY_WARNING_VOLTAGE		3.2


	#ifdef TX

        void InitializeBattery(void);
		void ReadBattery(void);
		float GetBatteryVoltage(void);
        bool IsBatteryOk(void);

	#endif



#endif