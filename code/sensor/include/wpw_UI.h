

#ifndef wpw_UI

    #define wpw_UI


    #include <Arduino.h>

    #include "wpw_Sensor.h"
	#include "wpw_Config.h"



    #define     MILLIS_PER_DAY          86400000
    #define     MILLIS_PER_HOUR         3600000
    #define     MILLIS_PER_MINUTE       60000
    #define     MILLIS_PER_SECOND       1000

	#define     SCREEN_REFRESH      	950
    #define		BLINK_ON_DURATION		400
	#define		BLINK_OFF_DURATION		300

	#define     FONT_LARGE            	u8g2_font_logisoso16_tr
	#define     FONT_MEDIUM         	u8g2_font_crox2h_tr //u8g2_font_helvR10_tr
	#define     FONT_SMALL          	u8g2_font_helvR08_tr


    struct Time
    {
        uint8_t Days;
        uint8_t Hours;
        uint8_t Minutes;
        uint8_t Seconds;
    };



	void InitializeDisplay(void);
    void PaintSplashScreen(void);
	void PaintPumpingScreen(uint8_t, uint8_t, uint32_t);

	void HandleDisplay();
    void RegisterDisplayRefresh(void);
	bool InSettingsMenu(void);
	bool IsDisplayPowered(void);

    void PaintMainScreen(void);
    void PaintMainHeader(void);
    void PaintSensorData(uint8_t, uint8_t, uint8_t);
	void PaintSettingScreen(void);
	void PaintSettingPosition(void);
	void PrintRadioPower(uint8_t);
    void PrintMoistureLevel(uint8_t, bool = false);

    Time GetTime(uint32_t);

	int32_t AddValueAndLimit(int32_t, int16_t, uint16_t, uint16_t, bool);

	uint16_t * GetDisplayTimeoutPointer(void);

	#ifdef DEBUG
		void SetDebugMessage(String);
	#endif


#endif