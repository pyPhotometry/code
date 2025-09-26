This folder contains json files specifying hardware configurations for different device types.  

You can create new custom device types by adding additonal json files.  

Device configurations specify the following variables:

# Pyboard Pins used for analog and digital signals.

    "pins":  
        "analog_1"
        "analog_2"
        "digital_1"
        "digital_2"

# Calibration of DAC values against LED currents: DAC_value = offset + slope * LED_current_mA.

    "LED_calibration": 
        "slope"
        "offset"

# Analog signal volts per division for signal [1, 2]

    "ADC_volts_per_division"

 
# Maximum value output by ADC for analog channels.
    "ADC_max_value"

# Maximum sampling rate in continuous and pulsed acquisition modes (Hz). For pulsed modes the max sampling rate is per analog channel.

    "max_sampling_rate"
        "continuous"
        "pulsed"

# Maximum LED current in continuous and time division acquisition modes (mA).

    "max_LED_current"
        "continuous"
        "pulsed"

# Rate at which ADC samples are aquired for oversampling.

    "oversampling_rate"
        "continuous"
        "pulsed"