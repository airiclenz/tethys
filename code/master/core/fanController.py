import lgpio
import time
from simple_pid import PID
from hardware import Pins
from gpiozero import CPUTemperature

# Set up GPIO
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, Pins.FAN)

# PID setup
pid = PID(1, 0.1, 0.05, setpoint=50)  # Adjust these values as needed
pid.output_limits = (0, 100)


# =============================================================================
def control_fan():
    '''Synchronous PID fan-control loop, run on its own daemon thread by the core
    (see tethys_core.main). One CPU-temperature read + PWM update per second.

    A transient sensor/GPIO error is logged and skipped rather than left to kill
    the thread -- an uncaught exception here would silently stop ALL fan control
    until the next core restart. The lgpio chip is released by the OS when the
    process exits (a daemon thread does not run a finally on shutdown), and the
    next core start re-opens and re-claims it cleanly.'''
    while True:
        try:
            control = pid(CPUTemperature().temperature)
            print(f"PWM value: {control}")
            lgpio.tx_pwm(chip, Pins.FAN, 100, control)  # 100Hz frequency
        except Exception as e:
            print(f"fan control loop error: {e}")
        time.sleep(1)



