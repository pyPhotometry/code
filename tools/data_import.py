# Function for opening pyPhotometry data files in Python.

import json
import numpy as np
from scipy.signal import butter, filtfilt

def import_ppd(file_path, low_pass=20, high_pass=0.01):
    with open(file_path, 'rb') as f:
        header_size = int.from_bytes(f.read(2), 'little')
        data_header = f.read(header_size)
        data = np.frombuffer(f.read(), dtype=np.dtype('<u2'))
    # Extract header information
    header_dict = json.loads(data_header)
    volts_per_division = header_dict['volts_per_division']
    sampling_rate = header_dict['sampling_rate']
    # Extract signals.
    analog  = data >> 1       # Analog signal is most significant 15 bits.
    digital = (data & 1) == 1 # Digital signal is least significant bit.
    # Alternating samples are signals 1 and 2.
    analog_1 = analog[ ::2] * volts_per_division[0]
    analog_2 = analog[1::2] * volts_per_division[1]
    digital_1 = digital[ ::2]
    digital_2 = digital[1::2]
    time = np.arange(analog_1.shape[0]) / sampling_rate # Time relative to start of recording (seconds).
    # Filter signals.
    if low_pass and high_pass:
        b, a = butter(2, np.array([high_pass, low_pass])/(0.5*sampling_rate), 'bandpass')
    elif low_pass:
        b, a = butter(2, low_pass/(0.5*sampling_rate), 'low')
    elif high_pass:
        b, a = butter(2, high_pass/(0.5*sampling_rate), 'high')
    if low_pass or high_pass:
        analog_1_filt = filtfilt(b, a, analog_1)
        analog_2_filt = filtfilt(b, a, analog_2)
    else:
        analog_1_filt = analog_2_filt = None
    # Return signals + header information as a dictionary.
    data_dict = {'analog_1'      : analog_1,
                 'analog_2'      : analog_2,
                 'analog_1_filt' : analog_1_filt,
                 'analog_2_filt' : analog_2_filt,
                 'digital_1'     : digital_1,
                 'digital_2'     : digital_2,
                 'time'          : time}
    data_dict.update(header_dict)
    return data_dict