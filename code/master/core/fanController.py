import lgpio
import asyncio
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
async def control_fan():
    try:
        while True:

            control = pid(CPUTemperature().temperature)
            print(f"PWM value: {control}")
            lgpio.tx_pwm(chip, Pins.FAN, 100, control)  # 100Hz frequency
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass

    finally:
        lgpio.gpiochip_close(chip)



