# Hardware config.

pins = {
    "analog_1": "X11",
    "analog_2": "X12",
    "digital_1": "Y7",
    "digital_2": "Y8",
}  # Pyboard Pins used for analog and digital signals.

LED_calibration = {
    "slope": 38.15,
    "offset": 6.26,
}  # Calibration of DAC values against LED currents: DAC_value = offset + slope * LED_current_mA.

ADC_volts_per_division = [0.00010122, 0.00010122]  # Analog signal volts per division for signal [1, 2]

max_sampling_rate = {
    "cont": 1000,
    "tdiv": 130,
}  # Maximum sampling rate in continous and time division acquisition modes (Hz).

max_LED_current = {
    "cont": 100,
    "tdiv": 100,
}  # Maximum LED current in continous and time division acquisition modes (mA).

oversampling_rate = {"cont": 3e5, "tdiv": 256e3}  # Rate at which ADC samples are aquired for oversampling.
