

#ifndef wpw_Sleep

    #define wpw_Sleep

    #include <Arduino.h>
    #include <avr/sleep.h>
    #include <avr/power.h>
    #include <avr/wdt.h>



    void InitializeSleep(void);
    void Sleep(void);

#endif
