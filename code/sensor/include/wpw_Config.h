

#ifndef wpw_Config

    #define wpw_Config

	#include <Arduino.h>
    #include <RF24.h>
	#include <wpw_Version.h>



    // ================================================ //
    // C H A N G E   T H E S E   A C C O R D I N G L Y  //
    // ================================================ //
                                                        //
    #define SENSOR_NUMBER       5 // 1-5    			//
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

	// Settle time (in seconds) after boot/calibration before the FIRST measurement
	// is taken and transmitted. The node sleeps through this window one ~9 s
	// watchdog loop at a time (it does NOT block), so it costs almost no power and
	// the effective resolution is ~9 s. Gives the probe time to reach its final
	// monitoring position before the first reported reading.
	#define		STARTUP_SETTLE_SECONDS	60


	// How often (in seconds) the node re-pulls its configuration from the master
	// while running. The pull rides an existing measurement wake (the radio is
	// already powered up), so it adds no extra radio power-up -- only a short
	// settings-only request on the first measurement at/after this interval has
	// elapsed since the last pull. The master answers from its config cache, so
	// the listen window is usually a few ms. Set to 0 to disable periodic pulls
	// entirely (maximum battery saving); the one-time boot-time fetch still
	// happens. NOTE: periodic pulls deliver measure-frequency / TX-power only --
	// calibration stays a boot-only, user-supervised operation.
	#define		PULL_CONFIG_CYCLE_SECONDS	3600	// 1 hour; 0 = disabled


	// ------------------------------------------------
	// Wire protocol (MUST stay in sync with code/master/core/protocol.py)

	// Bump whenever the on-air struct layout changes. A frame whose first byte
	// does not match is dropped instead of mis-parsed.
	#define		PROTOCOL_VERSION		1

	// Fixed on-air payload size in bytes. Both ends call setPayloadSize() with
	// this value; shorter frames are zero-padded by the radio. Must be >= the
	// largest message.
	#define		PAYLOAD_SIZE			8




    // ------------------------------------------------
    // Pin definitions

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
