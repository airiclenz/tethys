

#include <bitOps.h>

#include <wpw_Config.h>

#include <wpw_Battery.h>
#include <wpw_Blinker.h>
#include <wpw_EEPROM.h>
#include <wpw_RXTX.h>
#include <wpw_Sensor.h>
#include <wpw_WirelessPlantWatering.h>


RF24 radio(
    PIN_CE,
    PIN_CSN);


//const byte pipes[][6] =
const uint64_t pipes[] =
{
    PIPE_ADDRESS_0,         // RX
    PIPE_ADDRESS_1,         // TX (Sensor Number 1)
    PIPE_ADDRESS_2,         // TX (Sensor Number 2)
    PIPE_ADDRESS_3,         // TX (Sensor Number 3)
    PIPE_ADDRESS_4,         // TX (Sensor Number 4)
    PIPE_ADDRESS_5          // TX (Sensor Number 5)
};


uint8_t _statusTX = TX_INACTIVE;

uint8_t _powerLevel;

Package _package;



// =============================================================================
void InitializeRadio()
{
    radio.begin();

	_powerLevel = RF24_PA_LOW;

    radio.setAddressWidth(5);
    radio.setAutoAck(true);
    radio.setCRCLength(RF24_CRC_8);
    radio.setPALevel(_powerLevel);
    radio.setDataRate(RF24_250KBPS);

    // Fixed payload size on both ends: framing is explicit and the master never
    // has to guess a length. Must match PAYLOAD_SIZE in protocol.py.
    radio.setPayloadSize(PAYLOAD_SIZE);

    // Deterministic auto-ACK retransmission: 15 retries, 1500us apart.
    radio.setRetries(5, 15);

    //radio.enableAckPayload();
	//radio.enableDynamicPayloads();

}


// =============================================================================
uint8_t * GetTransmissionPowerPointer()
{
	return &_powerLevel;
}


// =============================================================================
void SetTransmissionPower()
{
	radio.setPALevel(_powerLevel);
}








// =============================================================================
uint8_t GetTxStatus()
{
	return _statusTX;
}


// =============================================================================
void SetupRadioForTx()
{
	radio.openWritingPipe(pipes[SENSOR_NUMBER]);
	radio.openReadingPipe(1, pipes[0]);

	radio.stopListening();

}


// =============================================================================
void RadioPowerUp()
{
	radio.powerUp();
}


// =============================================================================
void RadioPowerDown()
{
	radio.powerDown();
}


// =============================================================================
bool RequestConfiguration(
	bool periodic)
{
	RadioPowerUp();
	delay(5);
	SetupRadioForTx();

	Package package =
	{
		PROTOCOL_VERSION,
		periodic ? DATATYPE_CMD_GETCONFIG_PERIODIC : DATATYPE_CMD_GETCONFIG,
		0,
		0.0
	};

	// stop listening so we can talk
	radio.stopListening();

	//radio.write(&package, sizeof(Package));

	if (radio.write(&package, sizeof(Package)))
	{

		radio.startListening();

		uint32_t sendTime = millis();

		while (!radio.available())
		{
			// TIMEOUT --> Leave... the master answers from its config
			// cache, so 500ms is comfortable headroom over the radio
			// round-trip without burning much awake time.
			if (millis() > sendTime + 500)
			{
				radio.stopListening();
				RadioPowerDown();

				// Periodic pulls stay silent to save awake time; the
				// boot-time fetch keeps its "no master reply" blink.
				if (!periodic)
				{
					DoSimpleBlink(15,150);
					DoSimpleBlink(15,0);
				}

				return false;
			}
		}

		// Define an empty package
		ConfigurationPackage configPackage =
		{
			0,		// Protocol Version
			0,		// Data Type
			0,		// MeasureFrequency
			0,		// TransmissionPowerLevel
			false	// Trigger Calibration
		};

		while (radio.available())
		{
			radio.read(
				&configPackage,
				sizeof(ConfigurationPackage));
		}

		radio.stopListening();

		if (configPackage.ProtocolVersion == PROTOCOL_VERSION &&
			configPackage.PackageType == DATATYPE_CONFIG)
		{
			uint16_t * watchdogLoopsPtr = GetWatchdogLoopPointer();

			*watchdogLoopsPtr =
				round(
					(float)configPackage.MeasureFrequency * LOOPS_PER_MINUTE);

			radio.setPALevel(configPackage.TransmissionPowerLevel);

			// Calibration is a boot-only, user-supervised operation. A
			// periodic pull must never trigger it -- the master also forces
			// the flag off for the periodic opcode, so this is belt-and-
			// suspenders against an unexpected reply.
			if (!periodic && configPackage.TriggerCalibration)
			{
				Calibrate();
				SaveCalibrationToEeprom();
			}

			MakeSettingsFlagDirty();
			RadioPowerDown();

			// Config successfully received and applied: a soft ~2 s glow
			// (brightness ramps up then down) rather than a terse flash.
			// Periodic pulls stay silent to save awake time.
			if (!periodic)
			{
				DoSoftPulse(2000);
				delay(400);
			}
			return true;
		}
	}
	
	// Periodic pulls stay silent; the boot-time fetch keeps its
	// "config rejected" blink.
	if (!periodic)
	{
		DoSimpleBlink(15,150);
		DoSimpleBlink(15,150);
		DoSimpleBlink(15,0);
	}
	RadioPowerDown();
	return false;
}



// =============================================================================
void HandleTransmitter()
{
	_statusTX = TX_ACTIVE;

	uint8_t packageType = DATATYPE_SENSORDATA;

	// if the battery is close to being empty
	if (!IsBatteryOk())
	{
		packageType = DATATYPE_SENSORDATA_BATTERYALERT;
	}

	Package data =
	{
		PROTOCOL_VERSION,
		packageType,
		GetMoistureLevelPercent(),
		GetBatteryVoltage()
	};

	radio.stopListening();

	if (radio.write(
			&data,
			sizeof(data))
		)
	{
		_statusTX = TX_INACTIVE;
	}
	else
	{
		_statusTX = TX_FAILURE;
	}
}






