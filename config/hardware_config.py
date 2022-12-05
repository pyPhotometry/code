# Hardware config.

pins = {'analog_1' : 'X11', # Pyboard Pins used for analog and digital signals.
        'analog_2' : 'X12',
        'digital_1': 'Y7' ,
        'digital_2': 'Y8' }

LED_calibration = {'slope' : 38.15,  # Calibration of DAC values against LED currents.
                   'offset':  6.26}  # DAC_value = offset + slope * LED_current_mA.

ADC_volts_per_division = [0.00010122, 0.00010122] # Analog signal volts per division for signal [1, 2]

max_sampling_rate = {'cont': 1000, # Maximum sampling rate in continous and time division acquisition modes (Hz).
                     'tdiv': 130}

max_LED_current = {'cont': 100, # Maximum LED current in continous and time division acquisition modes (mA).
                   'tdiv': 100}

oversampling_rate = {'cont': 3e5, # Rate at which ADC samples are aquired for oversampling.
                     'tdiv': 256e3}

# Opto-pulse settings.

op_current_multipliers = [0,1,2,3,4,5] # Multiples of set current to cycle through.

op_pulse_dur = 200 # Duration of current pulse (ms).

op_IPI_dur = 10000 # Inter pulse interval (ms). 