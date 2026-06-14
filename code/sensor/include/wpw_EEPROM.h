

#ifndef wpw_EEPROM

    #define wpw_EEPROM


	void InitializeEeprom(void);
	void MakeSettingsFlagDirty(void);
	bool IsSettingsFlagDirty(void);
	void BlinkEepromSaveSuccess(void);
	void BlinkEepromNoChange(void);

	// showFeedback == false saves silently (no save/no-change blink). Used by
	// the TX node's periodic config pull, which must stay dark to save power.
	void SaveSettingsToEeprom(bool showFeedback = true);
	void ReadSettingsFromEeprom(void);



	void SaveCalibrationToEeprom(void);
	void ReadCalibrationFromEeprom(void);



#endif