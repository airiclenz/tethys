

#ifndef wpw_EEPROM

    #define wpw_EEPROM


	void InitializeEeprom(void);
	void MakeSettingsFlagDirty(void);
	bool IsSettingsFlagDirty(void);
	void BlinkEepromSaveSuccess(void);
	void BlinkEepromNoChange(void);

	void SaveSettingsToEeprom(void);
	void ReadSettingsFromEeprom(void);


	#ifdef TX

		void SaveCalibrationToEeprom(void);
		void ReadCalibrationFromEeprom(void);

	#endif


#endif