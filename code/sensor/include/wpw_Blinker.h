

#ifndef wpw_Blinker

    #define wpw_Blinker


    #include <Arduino.h>

	#include <wpw_Config.h>




    #define     BLINK_INACTIVE          B00000000
    #define     BLINK_ACTIVE            B00000001
    #define     BLINK_POST              B00000010

	
    #define		BLINK_ARRAY_LENGHT		10


	void DoSimpleBlink(uint16_t, uint16_t);


	#ifdef RX
    
		struct Blink
		{
			uint16_t BlinkDuration;
			uint16_t BlinkPostDuration;
		};


		void HandleBlinks(void);
		void AddBlinkToQueue(uint16_t, uint16_t);
		bool HasBlinksQueued(void);
		
	#endif
	
	

#endif