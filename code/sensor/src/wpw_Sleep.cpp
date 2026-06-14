

#include <wpw_Config.h>

#include <wpw_Sleep.h>


volatile uint8_t    _watchdog_event  = 1;


// POWER SAVING MEASURES:
// -	ADC disabled while sleep (saving ~250μA)
// -	BOD disabled in FUSES (saving ~19μA). This is not needed as the Li-Ion
// 		battery will go down to max 2.5V and the nRF module needs 3V anyways.
//		The ATTiny84 has a voltage range of 1.8 to 5.5V (@ 8MHz).
//
// Final Sleeping consumption is ~9 μA including the 3V LDO (up tp 3μA
// quiescent current) and the nRF24 module (900 nA in power down).


// ============================================================================
void Sleep_ADC()
{
	// disable the ADC as it uses ~250μA
	ADCSRA &= ~(1 << ADEN);
}



// ============================================================================
// here we put the arduino to sleep
void Sleep()
{
	
	// clear the Watchdog flag
	_watchdog_event = 0;


	/* Now is the time to set the sleep mode. In the Atmega8 datasheet
	* http://www.atmel.com/dyn/resources/prod_documents/doc2486.pdf on page 35
	* there is a list of sleep modes which explains which clocks and
	* wake up sources are available in which sleep mode.
	*
	* In the avr/sleep.h file, the call names of these sleep modes are to be found:
	*
	* The 5 different modes are:
	*     SLEEP_MODE_IDLE         -the least power savings
	*     SLEEP_MODE_ADC
	*     SLEEP_MODE_PWR_SAVE
	*     SLEEP_MODE_STANDBY
	*     SLEEP_MODE_PWR_DOWN     -the most power savings
	*
	* For now, we want as much power savings as possible, so we
	* choose the according
	* sleep mode: SLEEP_MODE_PWR_DOWN
	*
	*/

	// sleep mode is set here
	set_sleep_mode(SLEEP_MODE_PWR_DOWN);

	// enables the sleep bit in the mcucr register
	// so sleep is possible. just a safety pin
	sleep_enable();
	

	/* Disable all of the unused peripherals. This will reduce power
	* consumption further and, more importantly, some of these
	* peripherals may generate interrupts that will wake our Arduino from
	* sleep!
	*/

	//power_adc_disable();
	//power_spi_disable();
	//power_timer0_disable();
	//power_timer1_disable();
	//power_twi_disable();
	
	Sleep_ADC();
	
		
	/* Now it is time to enable an interrupt. We do it here so an
	* accidentally pushed interrupt button doesn't interrupt
	* our running program. if you want to be able to run
	* interrupt code besides the sleep function, place it in
	* setup() for example.
	*
	* In the function call attachInterrupt(A, B, C)
	* A   can be either 0 or 1 for interrupts on pin 2 or 3.
	*
	* B   Name of a function you want to execute at interrupt for A.
	*
	* C   Trigger mode of the interrupt pin. can be:
	*             LOW        a low level triggers
	*             CHANGE     a change in level triggers
	*             RISING     a rising edge of a level triggers
	*             FALLING    a falling edge of a level triggers
	*
	* In all but the IDLE sleep modes only LOW can be used.
	*/
			
											
	// here the device is actually put to sleep!!
	// THE PROGRAM CONTINUES FROM HERE AFTER WAKING UP
	sleep_mode();
							
	// z z z z z z z Z Z Z Z Z Z Z Z Z Z

	// first thing after waking from sleep:
	// disable sleep...
	sleep_disable();

	// Re-enable the peripherals.
	power_all_enable();

	
}


// ============================================================================
void InitializeSleep()
{
	/* Clear the reset flag. */
	MCUSR &= ~(1<<WDRF);
	
	/* In order to change WDE or the prescaler, we need to
	* set WDCE (This will allow updates for 4 clock cycles).
	*/
	WDTCSR |= (1<<WDCE) | (1<<WDE);

	/* set new watchdog timeout prescaler value */
	WDTCSR = 1<<WDP0 | 1<<WDP3; /* 8.0 seconds */
	
	/* Enable the WD interrupt (note no reset). */
	WDTCSR |= _BV(WDIE);

}



// ============================================================================
// Watchdog Interrupt Service. This is executed when watchdog timed out.
ISR(WDT_vect)
{
	if(_watchdog_event == 0)
	{
		_watchdog_event = 1;
	}

}



