

#ifndef wpw_Input

    #define wpw_Input

    #include <Arduino.h>







	// Button 1 pressed
	#define		B1_DOWN								BIT_0
	// Button 2 pressed
	#define 	B2_DOWN								BIT_1
	// DOUBLE Button pressed
	#define 	DOUBLE_DOWN							BIT_2
	// Single-Read-Flag Button 1 Press
	#define		SINGLEREAD_B1_PRESSED				BIT_3
	// Single-Read-Flag Button 2 Press
	#define		SINGLEREAD_B2_PRESSED				BIT_4
	// Single-Read-Flag Double Press
	#define		SINGLEREAD_DOUBLE_PRESSED			BIT_5
	// a post delay for double presses
	#define		DOUBLEPRESS_POSTDELAY				BIT_6
	// a post delay for single presses
	#define		SINGLEPRESS_POSTDELAY				BIT_7



	
	#define  	ACCELERATION_DELAY_DURATION			500
	#define		DEBOUNCE_DELAY_DURATION				75
	#define		DOUBLE_PRESS_POSTDELAY_DURATION		300
    #define		ACCELERATION_START_FACTOR			1.00001
	#define		ACCELERATION_LIMIT					5


	// Sweith this feature on / off
	#define		ACCELERATION_ENABLED		BIT_0
	// the delay after the key was just pressed
	// before the acceleration beginns
	#define 	ACCELERATION_INITIAL_DELAY	BIT_1
	// in acceleration phase
	#define		ACCELERATION_PHASE			BIT_2



    void HandleInput(void);
	int8_t HandleJog(void);

	bool IsDoublePress(void);
	bool IsButton1Press(void);
	bool IsButton2Press(void);

	void ActivateJogging(void);
	void DeactivateJogging(void);
	void DeleteSingleReadFlags(void);

    bool ReadWaterSensor(void);
    bool IsWaterOk(void);
	uint16_t GetWaterReadout(void);
	bool * GetUseWaterSensorPointer(void);

	void InterruptButton1(void);
	void InterruptButton2(void);


#endif