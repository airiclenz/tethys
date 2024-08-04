

#ifndef wpw_Pumps

    #define wpw_Pumps


    #include <Arduino.h>

	#include <wpw_Config.h>


	#ifdef RX

		void HandlePumpsAndValves(void);

		void SetValveStatus(uint8_t, bool);
		void DoPumping(uint8_t, uint8_t, uint16_t);

	#endif


#endif