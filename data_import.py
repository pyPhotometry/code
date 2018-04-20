# Function for opening pyPhotometry data files in Python.

from datetime import datetime
import numpy as np

def import_data(file_path):
    with open(file_path, 'rb') as f:
        header_size = int.from_bytes(f.read(2), 'little')
        data_header = f.read(header_size)
        data = np.frombuffer(f.read(), dtype=np.dtype('<u2'))
    # Extract header information
    subject_ID = data_header[:12].decode().strip()
    date_time = datetime.strptime(data_header[12:31].decode(), '%Y-%m-%dT%H:%M:%S')
    mode = {1: 'GCaMP/RFP', 2:'GCaMP/iso'}[data_header[31]]
    sampling_rate = int.from_bytes(data_header[32:34], 'little')
    volts_per_division = np.frombuffer(data_header[34:42], dtype='<u4')*1e-9
    # Extract signals.
    signal  = data >> 1       # Analog signal is most significant 15 bits.
    digital = (data % 2) == 1 # Digital signal is least significant bit.
    # Alternating samples are signals 1 and 2.
    ADC1 = signal[ ::2] * volts_per_division[0]
    ADC2 = signal[1::2] * volts_per_division[1]
    DI1 = digital[ ::2]
    DI2 = digital[1::2]    
    return {'subject_ID'   : subject_ID,
            'datetime'     : date_time,
            'datetime_str' : date_time.strftime('%Y-%m-%d %H:%M:%S'),
            'mode'         : mode,
            'sampling_rate': sampling_rate,
            'volts_per_div': volts_per_division,
            'ADC1'     : ADC1,
            'ADC2'     : ADC2,
            'DI1'    : DI1,
            'DI2'    : DI2}
