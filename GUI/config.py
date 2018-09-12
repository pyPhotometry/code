VERSION = 0.1 # Version number of pyPhotometry.

# ----------------------------------------------------------------------------------------
# GUI Config
# ----------------------------------------------------------------------------------------

history_dur   = 10       # Duration of plotted signal history (seconds)
triggered_dur = [-3,6.9] # Window duration for event triggered signals (seconds pre, post)
update_interval = 5      # Interval between calls to update function (ms).

default_LED_current = [10,10] # Channel [1, 2] (mA).

default_mode = '2 colour continuous' # Default acquisition mode, valid values are: '2 colour continuous', '1 colour time div.', '2 colour time div.'

# ----------------------------------------------------------------------------------------
# Hardware config.
# ----------------------------------------------------------------------------------------

pins = {'analog_1' : 'X11', # Pyboard Pins used for analog and digital signals.
        'analog_2' : 'X12',
        'digital_1': 'Y7' ,
        'digital_2': 'Y8' }

LED_calibration = {'slope' : 38.15,  # Calibration of DAC values against LED currents.
                   'offset':  6.26}  # DAC_value = offset + slope * LED_current_mA.

ADC_volts_per_division = [0.00010122, 0.00010122] # Analog signal volts per division for signal [1, 2]