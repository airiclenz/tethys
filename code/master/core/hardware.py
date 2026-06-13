# =============================================================================
# =============================================================================
# =============================================================================
class Pins:
    # Radio related
    IRQ = 17
    CSN = 0
    CE = 22

    # channel and pump related
    PUMP = 6

    CHANNELS = [16, 19, 20, 26, 21]
    # TODO: a 6th channel needs a physical GPIO pin assigned here before it can
    # be driven. The database/radio already reference 6 channels; the hardware
    # currently exposes 5. CHANNEL_COUNT is the single source of truth.

    # The water sensor pin
    WATER_SENSOR = 4

    # The debugging / status LED
    LED = 14

    FAN = 15


# Single source of truth for how many watering channels physically exist.
CHANNEL_COUNT = len(Pins.CHANNELS)
