

#ifndef wpw_Config

    #define wpw_Config

	#include <Arduino.h>
	//#include <avr/io.h>
    #include <RF24.h>
	#include <wpw_Version.h>



    // ================================================ //
    // C H A N G E   T H E S E   A C C O R D I N G L Y  //
    // ================================================ //
                                                        //
    // Chose only ONE - valid: TX or RX                 //
    ///////////////////////////////////	                //
	//													//
	//#define RX  	    								//
	#define TX  										//
    #define SENSOR_NUMBER       2 // 1-5    			//
                                                        //
	////////////////////////////////////                //
                                                        //
	//#define DEBUG				 						//
                                                        //
    // Change the first 4 bytes to be identical for		//
	// giving a certain namespace			            //
	// The last byte needs to be unique for each pipe.	//
    #define PIPE_ADDRESS_0      0x5232443230  			//
    #define PIPE_ADDRESS_1      0x5232443231  			//
    #define PIPE_ADDRESS_2      0x5232443232  			//
    #define PIPE_ADDRESS_3      0x5232443233  			//
    #define PIPE_ADDRESS_4      0x5232443234  			//
    #define PIPE_ADDRESS_5      0x5232443235  			//
                                                        //
    // ================================================ //


	#define		LOOPS_PER_MINUTE		6.667		// 9 sec per loop




    // ------------------------------------------------
    // Definitions for Transmitter
    #ifdef TX

        #include "wpw_Sleep.h"

        #define     PIN_CE              8
        #define     PIN_CSN             9
        #define     PIN_LED             10
        #define     PIN_BATTERY         A7

		// Port descriptions here as these
		// are used to set port bits:
        #define     PIN_SENSOR_CLOCK    PB2
        #define     PIN_SENSOR_READ     PA3

    #endif



    // ------------------------------------------------
    // Definitions for Receiver
    #ifdef RX

        #include <U8g2lib.h>

		#define     PIN_CE              4
        #define     PIN_CSN             11
		#define     PIN_LED             13

		#define     PIN_WATER           A1
        #define     PIN_BUTTON_1        1
        #define     PIN_BUTTON_2        0


        #define     PIN_VALVE_1     	12
        #define     PIN_VALVE_2			6
        #define     PIN_VALVE_3			8
        #define     PIN_VALVE_4			9
        #define     PIN_VALVE_5			10
		#define		PIN_PUMP			5

    #endif



#endif
