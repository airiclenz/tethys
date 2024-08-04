

#include <Arduino.h>
#include <bitOps.h>

#include "wpw_Config.h"

#include "wpw_UI.h"
#include "wpw_EEPROM.h"
#include "wpw_Input.h"
#include "wpw_Pumps.h"
#include "wpw_RXTX.h"
#include "wpw_Sensor.h"



#ifdef RX


    #define     DISPLAY_DOREFRESH       BIT_0
    #define     DISPLAY_MAINSCREEN      BIT_1
    #define     DISPLAY_SETTINGS        BIT_2
    #define     DISPLAY_POWERED         BIT_3
	#define     DISPLAY_EDITMODE        BIT_4
	#define     DISPLAY_EDITBLINK       BIT_5


	uint8_t _sensorNumber 			=	0;



	#define 	SETTING_COUNT			13


	const char _settingStrings[SETTING_COUNT][17] =
	{
		"Channel Number",
		"Enabled",
		"Channel Type",
		"Measure Freq.",
		"Trigger Level",
		"Pump Duration",
		"RF-Power",
		"Test",
		"Calibrate",
		"Master RF-Power",
		"Use Water Sensor",
		"Display Timeout",
		"Exit"
	};





    // ------------------------------------------------
    // ICONS


	const unsigned char iconWater5[] PROGMEM =
		{ 0xbd, 0xbd, 0xbd, 0xbd, 0xbd, 0xbd, 0x81, 0x7e };

	const unsigned char iconWater4[] PROGMEM =
		{ 0x81, 0x81, 0xbd, 0xbd, 0xbd, 0xbd, 0x81, 0x7e };

	const unsigned char iconWater3[] PROGMEM =
		{ 0x81, 0x81, 0x81, 0x81, 0xbd, 0xbd, 0x81, 0x7e };

	const unsigned char iconWater2[] PROGMEM =
		{ 0x81, 0x81, 0x81, 0x81, 0x81, 0xbd, 0x81, 0x7e };

	const unsigned char iconWater1[] PROGMEM =
		{ 0x81, 0x81, 0x81, 0x81, 0x81, 0x81, 0x81, 0x7e };



	const unsigned char iconX[] PROGMEM =
		{ 0x00, 0x00, 0x00, 0x00, 0x5a, 0x00, 0x00, 0x00 };

	const unsigned char iconEdit[] PROGMEM =
		{ 0x20, 0x70, 0xe8, 0x44, 0x22, 0x11, 0x0b, 0x07 };

	const unsigned char iconWarning[] PROGMEM =
		{ 0x18, 0x18, 0x18, 0x18, 0x18, 0x00, 0x18, 0x18 };



    // Defining the type of display used (128x64)
    U8G2_SSD1306_128X64_NONAME_F_HW_I2C oledDisplay(
        U8G2_R0,
        U8X8_PIN_NONE);


    uint32_t _lastDisplayUpdate			= 0;
    uint32_t _lastDisplayActionTime     = 0;
	uint32_t _lastEditBlinkAction		= 0;
    uint16_t _displayTimeoutSec         = 0;

	int8_t _showSensorDataTypeId		= 0;

    uint8_t  _statusDisplay             = DISPLAY_POWERED |
                                          DISPLAY_MAINSCREEN;

	uint8_t _settingPage 				= 0;



	#ifdef DEBUG

		String	_debugMessageOld			= "";
		String 	_debugMessage				= "";


		// =============================================================================
		void SetDebugMessage(
			String message)
		{
			message.concat(" ");
			message.concat(millis() / 100);

			_debugMessageOld = _debugMessage;
			_debugMessage = message;
		}

	#endif


	// ============================================================================
	uint16_t * GetDisplayTimeoutPointer()
	{
		return &_displayTimeoutSec;
	}


    // ============================================================================
    void InitializeDisplay()
    {
        oledDisplay.begin();

		_displayTimeoutSec = 60;
    }

	// =============================================================================
	bool InSettingsMenu()
	{
		return isBit(_statusDisplay, DISPLAY_SETTINGS);
	}

    // =============================================================================
    void DisplayDisable()
    {
        oledDisplay.clearBuffer();
        oledDisplay.sendBuffer();

        deleteBit(_statusDisplay, DISPLAY_POWERED);
    }


    // =============================================================================
    void RegisterDisplayRefresh()
    {
		// if the display is not powered, remove the button flags so that
		// we don't do anything else than waking up the display with the first
		// input event
		if (!isBit(_statusDisplay, DISPLAY_POWERED))
		{
			DeleteSingleReadFlags();
		}

        setBit(_statusDisplay, DISPLAY_POWERED);
        setBit(_statusDisplay, DISPLAY_DOREFRESH);

        _lastDisplayActionTime = millis();
    }



    // ============================================================================
    void HandleDisplay()
    {

		// both buttons pressed?
		if (IsDoublePress())
		{

			if (isBit(_statusDisplay, DISPLAY_MAINSCREEN))
			{
				deleteBit(_statusDisplay, DISPLAY_MAINSCREEN);
				setBit(_statusDisplay, DISPLAY_SETTINGS);
				_settingPage = 0;
			}

			else if (isBit(_statusDisplay, DISPLAY_SETTINGS))
			{
				// are we on the last page, the EXIT screen?
				if (_settingPage == SETTING_COUNT - 1)
				{
					deleteBit(_statusDisplay, DISPLAY_SETTINGS);
					setBit(_statusDisplay, DISPLAY_MAINSCREEN);

					// save the settings if changed
					if (IsSettingsFlagDirty())
					{
						SaveSettingsToEeprom();
					}
				}

				// are we on the testing screen?
				else if (_settingPage == 7)
				{
					Sensor * sensorPtr = GetSensorPointer(_sensorNumber);

					if (isBit((*sensorPtr).Status, CHANNEL_TYPE_ISVALVE))
					{
						SetValveStatus(_sensorNumber + 1, HIGH);

						DoPumping(
							_sensorNumber + 1,
							6,
							1);

						SetValveStatus(_sensorNumber + 1, LOW);
					}
					else
					{
						DoPumping(
							_sensorNumber + 1,
							_sensorNumber + 1,
							1);
					}

				}
				else
				{
					toggleBit(_statusDisplay, DISPLAY_EDITMODE);

					if (isBit(_statusDisplay, DISPLAY_EDITMODE))
					{
						// start with blink = on for immediate user
						// feedback
						setBit(_statusDisplay, DISPLAY_EDITBLINK);
						_lastEditBlinkAction = millis();

						ActivateJogging();
					}
					else
					{
						// disable the edit value blink when not in
						// edit mode so that the pen is not painted
						deleteBit(_statusDisplay, DISPLAY_EDITBLINK);

						DeactivateJogging();
					}
				}
			}
		}


		// toggle through the different sensor data options
		// when any button is pressed on the main screen
		if (isBit(_statusDisplay, DISPLAY_MAINSCREEN))
		{
			if (IsButton1Press())
			{
				_showSensorDataTypeId++;
				if (_showSensorDataTypeId > 5)
				{
					_showSensorDataTypeId = 0;
				}
			}
			else if (IsButton2Press())
			{
				_showSensorDataTypeId--;
				if (_showSensorDataTypeId < 0)
				{
					_showSensorDataTypeId = 5;
				}
			}
		}



		// edit mode? handle the value blinking
		if (isBit(_statusDisplay, DISPLAY_EDITMODE))
		{
			if (isBit(_statusDisplay, DISPLAY_EDITBLINK) &&
				millis() > _lastEditBlinkAction + BLINK_ON_DURATION)
			{
				_lastEditBlinkAction = millis();
				toggleBit(_statusDisplay, DISPLAY_EDITBLINK);
			}

			if (!isBit(_statusDisplay, DISPLAY_EDITBLINK) &&
				millis() > _lastEditBlinkAction + BLINK_OFF_DURATION)
			{
				_lastEditBlinkAction = millis();
				toggleBit(_statusDisplay, DISPLAY_EDITBLINK);
			}

			//setBit(_statusDisplay, DISPLAY_DOREFRESH);
		}



		// The actual display stuff
        if (isBit(_statusDisplay, DISPLAY_POWERED))
        {

            if (isBit(_statusDisplay, DISPLAY_DOREFRESH) ||
				isBit(_statusDisplay, DISPLAY_EDITMODE) ||
                millis() > _lastDisplayUpdate + SCREEN_REFRESH)
            {
                setBit(_statusDisplay, DISPLAY_POWERED);

				oledDisplay.clearBuffer();

                if (isBit(_statusDisplay, DISPLAY_MAINSCREEN))
                {
                    PaintMainScreen();
                }
				else if (isBit(_statusDisplay, DISPLAY_SETTINGS))
				{
					PaintSettingScreen();
				}

				#ifdef DEBUG

					if (_debugMessage != "")
					{
						oledDisplay.setFont(FONT_SMALL);
						oledDisplay.setCursor(0, 52);
						oledDisplay.print(_debugMessageOld);
						oledDisplay.setCursor(0, 62);
						oledDisplay.print(_debugMessage);
					}

				#endif

                oledDisplay.sendBuffer();

                _lastDisplayUpdate = millis();
                deleteBit(_statusDisplay, DISPLAY_DOREFRESH);

            }

            if (millis() > _lastDisplayActionTime + ((uint32_t)_displayTimeoutSec * (uint32_t)1000))
            {
                DisplayDisable();
            }
        }

    }


    // =============================================================================
    void PaintMainScreen()
    {
        PaintMainHeader();

        for (int i=0; i<5; i++)
        {
            PaintSensorData(i, 0,  24 + (i * 10));
        }


    }

    // =============================================================================
    void PaintMainHeader()
    {
        oledDisplay.setFont(FONT_SMALL);
        oledDisplay.setCursor(0, 10);
        oledDisplay.print(F("W:"));

		if (IsWaterOk())
		{
			oledDisplay.print(F(" OK"));
		}
		else
		{
			oledDisplay.print(F(" -"));
		}


        oledDisplay.setCursor(36, 10);
        oledDisplay.print(F("UpT: "));

        Time time = GetTime(millis());

        if (time.Days == 0)
        {
            oledDisplay.print(F("00d "));
        }
        else if (time.Days < 10)
        {
            oledDisplay.print(F("0"));
            oledDisplay.print(time.Days);
            oledDisplay.print(F("d "));
        }
        else
        {
            oledDisplay.print(time.Days);
            oledDisplay.print(F("d "));
        }

        if (time.Hours < 10)
        {
            oledDisplay.print(F("0"));
        }
        oledDisplay.print(time.Hours);
        oledDisplay.print(F("h"));

        if (time.Minutes < 10)
        {
            oledDisplay.print(F("0"));
        }
        oledDisplay.print(time.Minutes);
        oledDisplay.print(F(":"));

        if (time.Seconds < 10)
        {
            oledDisplay.print(F("0"));
        }
        oledDisplay.print(time.Seconds);


    }


    // =============================================================================
    void PaintSensorData(
        uint8_t sensorNumber,
        uint8_t x,
        uint8_t y)
    {
        oledDisplay.setFont(FONT_SMALL);
        oledDisplay.setCursor(x, y);
        oledDisplay.print(sensorNumber + 1);
        oledDisplay.print(F(":"));

		Sensor * sensorsPtr = GetSensorPointer(sensorNumber);

        if (!isBit((*sensorsPtr).Status, CHANNEL_ENABLED))
		{
			oledDisplay.print(F(" deactivated"));
			return;
		}


        else if ((*sensorsPtr).PackageCount > 0)
        {

			// if the sensor sent a battery alert
			if (isBit((*sensorsPtr).Status, CHANNEL_BATTERY_ALERT))
			{
				oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconWarning);
			}

			// otherwise display the moisture level
			else
			{

				switch ((*sensorsPtr).MoistureLevel)
				{
					case 1:
						oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconWater1);
						break;

					case 2:
						oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconWater2);
						break;

					case 3:
						oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconWater3);
						break;

					case 4:
						oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconWater4);
						break;

					case 5:
						oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconWater5);
						break;
				}
			}



			oledDisplay.setCursor(x + 27, y);
			switch (_showSensorDataTypeId)
			{
				case 0:
					oledDisplay.print(F("Chk#:"));
					oledDisplay.print((*sensorsPtr).PackageCount);
					break;

				case 1:
					oledDisplay.print(F("Pmp#:"));
					oledDisplay.print((*sensorsPtr).PumpCount);
					break;

				case 2:
					oledDisplay.print(F("Trg:"));
					PrintMoistureLevel(
						(*sensorsPtr).TriggerLevel,
						true);
					break;
					
				case 3:
					oledDisplay.print(F("Mst:"));
					PrintMoistureLevel(
						(*sensorsPtr).MoistureLevel,
						true);
					break;
					
				case 4:
					oledDisplay.print(F("Mst:"));
					oledDisplay.print((*sensorsPtr).MoistureLevelPercent);
					oledDisplay.print(F("%"));
					break;

				case 5:
					oledDisplay.print(F("Bat:"));
					oledDisplay.print((*sensorsPtr).BatteryVoltage, 2);
					oledDisplay.print(F("V"));
					break;
			}


            // TIME DSIPLAY
            uint32_t timeToLastMessage =
                millis() - (*sensorsPtr).Timestamp;

            Time time = GetTime(timeToLastMessage);

            oledDisplay.setCursor(x + 82, y);

            if (time.Days != 0)
            {
                oledDisplay.print(time.Days);
                oledDisplay.print(F(" day(s)"));
            }
            else
            {
                if (time.Hours < 10)
                {
                    oledDisplay.print(F("0"));
                }
                oledDisplay.print(time.Hours);
                oledDisplay.print(F("h"));

                if (time.Minutes < 10)
                {
                    oledDisplay.print(F("0"));
                }
                oledDisplay.print(time.Minutes);
                oledDisplay.print(F(":"));

                if (time.Seconds < 10)
                {
                    oledDisplay.print(F("0"));
                }
                oledDisplay.print(time.Seconds);
            }

        }
        else
        {
            oledDisplay.drawXBMP( x + 13, y - 8, 8, 8, iconX);
        }

    }


	// =============================================================================
	void PaintSettingScreen()
	{

		int8_t delta = 0;
		uint16_t hours;
		uint16_t minutes;
		uint8_t seconds;


		if (isBit(_statusDisplay, DISPLAY_EDITMODE))
		{
			delta = HandleJog();

			// only save the settings if someting was changed
			if (delta != 0)
			{
				MakeSettingsFlagDirty();
			}
		}
		else
		{
			if (IsButton1Press())
			{
				_settingPage =
					AddValueAndLimit(
						_settingPage,
						-1,
						0, SETTING_COUNT - 1,
						true);
			}

			if (IsButton2Press())
			{
				_settingPage =
					AddValueAndLimit(
						_settingPage,
						+1,
						0, SETTING_COUNT - 1,
						true);
			}

		}



		oledDisplay.drawVLine( 123,  16,  50);
		PaintSettingPosition();

		oledDisplay.setFont(FONT_MEDIUM);
		oledDisplay.setCursor(0, 13);

		if (_settingPage > 0 &&
			_settingPage < SETTING_COUNT - 4)
		{
			oledDisplay.print(F("Ch"));
			oledDisplay.print(_sensorNumber + 1);
			oledDisplay.print(F(":"));
		}


		if (isBit(_statusDisplay, DISPLAY_EDITBLINK))
		{
			oledDisplay.drawXBMP(120, 5, 8, 8, iconEdit);
		}


		oledDisplay.print(_settingStrings[_settingPage]);

		Sensor * sensorsPtr = GetSensorPointer(_sensorNumber);
		uint8_t * radioPowerPtr = GetTransmissionPowerPointer();
		bool * useWaterSensorPtr = GetUseWaterSensorPointer();


		oledDisplay.setCursor(0, 36);
		oledDisplay.setFont(FONT_LARGE);

		switch (_settingPage)
		{

			// SENSOR NUMBER
			case 0:

				_sensorNumber =
					AddValueAndLimit(
						_sensorNumber,
						delta,
						0, SENSOR_COUNT - 1,
						false);

				oledDisplay.print(_sensorNumber + 1);
				break;

			// ENABLE
			case 1:

				if (delta != 0)
				{
					toggleBit((*sensorsPtr).Status, CHANNEL_ENABLED);
				}

				if (isBit((*sensorsPtr).Status, CHANNEL_ENABLED))
				{
					oledDisplay.print(F("Yes"));
				}
				else
				{
					oledDisplay.print(F("No"));
				}
				break;

			// CHANNEL TYPE
			case 2:

				if (delta != 0)
				{
					toggleBit((*sensorsPtr).Status, CHANNEL_TYPE_ISVALVE);
				}

				if (isBit((*sensorsPtr).Status, CHANNEL_TYPE_ISVALVE))
				{
					oledDisplay.print(F("Valve"));
				}
				else
				{
					oledDisplay.print(F("Pump"));
				}
				break;

			// MEASURE FREQUENCY
			case 3:

				(*sensorsPtr).MeasureFrequency =
					AddValueAndLimit(
						(*sensorsPtr).MeasureFrequency,
						delta * 5,
						1, 2880,	// 1min - 48h
						false);

				hours = (*sensorsPtr).MeasureFrequency / 60;
				minutes = (*sensorsPtr).MeasureFrequency - (hours * 60);

				if (hours > 0)
				{
					oledDisplay.print(hours);
					oledDisplay.print(F("h "));
				}

				if (minutes > 0)
				{
					oledDisplay.print(minutes);
					oledDisplay.print(F("min"));
				}

				break;

			// TRIGGER LEVEL / MOISTURE LEVEL
			case 4:

				(*sensorsPtr).TriggerLevel =
					AddValueAndLimit(
						(*sensorsPtr).TriggerLevel,
						delta,
						MoistureLevel::Dusty, MoistureLevel::Wet,
						false);

				PrintMoistureLevel(
					(*sensorsPtr).TriggerLevel);
				break;

			// PUMP DURATION
			case 5:

				(*sensorsPtr).PumpDuration =
					AddValueAndLimit(
						(*sensorsPtr).PumpDuration,
						delta,
						1, 600,
						false);

				oledDisplay.print((*sensorsPtr).PumpDuration);
				oledDisplay.print(F("sec"));
				break;

			// SENSOR RADIO POWER
			case 6:

				(*sensorsPtr).TransmissionPower =
					AddValueAndLimit(
						(*sensorsPtr).TransmissionPower,
						delta,
						0, 3,
						false);

				PrintRadioPower((*sensorsPtr).TransmissionPower);
				break;


			// TEST PUMP
			case 7:

				oledDisplay.setFont(FONT_MEDIUM);
				oledDisplay.setCursor(0, 34);
				oledDisplay.print(F("Press both buttons"));
				oledDisplay.setCursor(0, 48);
				oledDisplay.print(F("to TEST for 1 sec."));
				break;

			// TRIGGER CALIBRATION
			case 8:

				if (delta != 0)
				{
					toggleBit((*sensorsPtr).Status, CHANNEL_CALIBRATE);
				}

				if (isBit((*sensorsPtr).Status, CHANNEL_CALIBRATE))
				{
					oledDisplay.print(F("Trigger Cal."));
				}
				else
				{
					oledDisplay.print(F("No Cal."));
				}
				break;

			// MASTER RADIO POWER
			case 9:

				*radioPowerPtr =
					AddValueAndLimit(
						*radioPowerPtr,
						delta,
						0, 3,
						false);

				PrintRadioPower(*radioPowerPtr);
				SetTransmissionPower();
				break;


			// USE WATER SENSOR
			case 10:

				if (delta != 0)
				{
					*useWaterSensorPtr = !(*useWaterSensorPtr);
				}

				if (*useWaterSensorPtr)
				{
					oledDisplay.print(F("Yes"));
				}
				else
				{
					oledDisplay.print(F("No"));
				}
				break;

			// DISPLAY TIMEOUT
			case 11:

				_displayTimeoutSec =
					AddValueAndLimit(
						_displayTimeoutSec,
						delta * 5,
						10, 600,
						false);

				minutes = _displayTimeoutSec / 60;
				seconds = _displayTimeoutSec - (minutes * 60);

				if (minutes > 0)
				{
					oledDisplay.print(minutes);
					oledDisplay.print(F("min "));
				}

				if (seconds > 0)
				{
					oledDisplay.print(seconds);
					oledDisplay.print(F("sec"));
				}

				break;

			// EXIT
			case 12:

				oledDisplay.setFont(FONT_MEDIUM);
				oledDisplay.setCursor(0, 34);
				oledDisplay.print(F("Press both buttons"));
				oledDisplay.setCursor(0, 48);
				oledDisplay.print(F("to EXIT..."));
				break;

		}

	}


	// =============================================================================
	void PrintRadioPower(uint8_t value)
	{

		// min, low, high, max
		// 0 dBm, -6 dBm, -12 dBm or -18 dBm
		switch (value)
		{
			case RF24_PA_MIN:
				oledDisplay.print(F("Min"));
				break;

			case RF24_PA_LOW:
				oledDisplay.print(F("Low"));
				break;

			case RF24_PA_HIGH:
				oledDisplay.print(F("High"));
				break;

			case RF24_PA_MAX:
				oledDisplay.print(F("Max"));
				break;

		}

	}

	// =============================================================================
	void PrintMoistureLevel(
		uint8_t value,
		bool useShort)
	{

		switch (value)
		{
			case MoistureLevel::Dusty:
				oledDisplay.print(F("Dusty"));
				break;

			case MoistureLevel::Dry:
				oledDisplay.print(F("Dry"));
				break;

			case MoistureLevel::Medium:
				if (useShort)
				{
					oledDisplay.print(F("Med."));
				}
				else
				{
					oledDisplay.print(F("Medium"));
				}
				break;

			case MoistureLevel::Moist:
				oledDisplay.print(F("Moist"));
				break;

			case MoistureLevel::Wet:
				oledDisplay.print(F("Wet"));
				break;
		}

	}


	// =============================================================================
    void PaintSettingPosition()
    {
		// display height = 64
		// the top 16 pixel are yellow - we will not use them --> height = 50
        float height = 48.0 / (float)SETTING_COUNT;

        oledDisplay.drawBox(
            126,
			(ceil)((_settingPage * height) + 16),
            2,
            floor(height)
		);

    }


	// =============================================================================
	void PaintChannelName(
		uint8_t channelNumber,
		uint8_t portNumber)
	{
		oledDisplay.print(F("Channel: "));

		if (portNumber == 6)
		{
			oledDisplay.print(channelNumber);
			oledDisplay.print(F(" [Valve]"));
		}
		else
		{
			oledDisplay.print(channelNumber);
			oledDisplay.print(F(" [Pump]"));
		}

	}

	// =============================================================================
	void PaintPumpingScreen(
		uint8_t channelNumber,
		uint8_t portNumber,
		uint32_t remainingTime)
	{
		Time time =
			GetTime(remainingTime);

		// clear the display
		oledDisplay.clearBuffer();

		oledDisplay.setFont(FONT_MEDIUM);
		oledDisplay.setCursor(0, 13);

		PaintChannelName(
			channelNumber,
			portNumber);

		oledDisplay.setFont(FONT_LARGE);
		oledDisplay.setCursor(0, 40);
		oledDisplay.print(F("Pumping..."));

		oledDisplay.setFont(FONT_MEDIUM);
		oledDisplay.setCursor(0, 60);

		if (time.Minutes != 0)
		{
			oledDisplay.print(time.Minutes);
        	oledDisplay.print(F(" min "));
		}

        if (time.Seconds < 10)
        {
            oledDisplay.print(F("0"));
        }

        oledDisplay.print(time.Seconds);
		oledDisplay.print(F(" sec"));

		oledDisplay.sendBuffer();
	}


    // =============================================================================
    void PaintSplashScreen()
    {
        oledDisplay.firstPage();
        do
        {
            oledDisplay.setFont(FONT_MEDIUM);
            oledDisplay.setCursor(26, 15);
            oledDisplay.print(F("Water-Plant"));

            oledDisplay.setFont(FONT_SMALL);
            oledDisplay.setCursor(26, 28);
            oledDisplay.print(F("version "));
			oledDisplay.print(VERSION);
			oledDisplay.print(F("."));
			oledDisplay.print(SUBVERSION);
			oledDisplay.print(F("."));
			oledDisplay.print(BUILDNUMBER);

        }
        while ( oledDisplay.nextPage() );

        delay(2000);
    }


	// =============================================================================
	bool IsDisplayPowered()
	{
		return isBit(_statusDisplay, DISPLAY_POWERED);
	}


    // =============================================================================
    Time GetTime(
        uint32_t duration)
    {

        Time result =
        {
            0,0,0,0
        };

        result.Days = duration / MILLIS_PER_DAY;
        duration -= result.Days * MILLIS_PER_DAY;

        result.Hours = duration / MILLIS_PER_HOUR;
        duration -= result.Hours * MILLIS_PER_HOUR;

        result.Minutes = duration / MILLIS_PER_MINUTE;
        duration -= result.Minutes * MILLIS_PER_MINUTE;

        result.Seconds = duration / MILLIS_PER_SECOND;

        return result;

    }


	// =============================================================================
    int32_t AddValueAndLimit(
        signed long value,
		int16_t delta,
        uint16_t min,
        uint16_t max,
        bool roleover)
    {

		value += delta;

        if (value > max)
        {
			if (roleover)
			{
				return min;
			}
			else
			{
				return max;
			}

        }

        else if (value < min)
        {
            if (roleover)
			{
				return max;
			}
			else
			{
				return min;
			}
        }

		return value;
    }





#endif