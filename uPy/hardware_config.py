#  This file specifies properties of the pyPhotometry hardware.

# Copyright (c) Thomas Akam 2018.  Licenced under the GNU General Public License v3.

pins = {'analog_1' : 'X11', # Pyboard Pins used for analog and digital signals.
        'analog_2' : 'X12',
        'digital_1': 'Y7' ,
        'digital_2': 'Y8' }

LED_calibration = {'slope' : 38.15,  # Calibration of DAC values against LED currents.
                   'offset':  6.26}  # DAC_value = offset + slope * LED_current_mA.

ADC_volts_per_division = [0.00010122, 0.00010122] # Analog signal volts per division for signal [1, 2]
