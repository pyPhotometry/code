# Code which runs on host computer and implements communication with pyboard.

import os
import numpy as np
from datetime import datetime
from pyboard import Pyboard

class Photometry_host(Pyboard):
    '''Class for aquiring data from a micropython photometry system on a host computer.'''

    def __init__(self, port, pins, mode='GCaMP/iso'):
        '''Open connection to pyboard and instantiate Photometry class on pyboard with
        provided parameters.'''
        assert mode in ['GCaMP/RFP', 'GCaMP/iso'], \
            "Invalid mode, value values: 'GCaMP/RFP' or 'GCaMP/iso'."
        self.mode = mode
        if mode == 'GCaMP/RFP':   # 2 channel GFP/RFP acquisition mode.
            self.max_rate = 1000  # Maximum sampling rate allowed for this mode.
        elif mode == 'GCaMP/iso': # GCaMP and isosbestic using time division multiplexing.
            self.max_rate = 160   # Hz.
        self.set_sampling_rate(self.max_rate)
        self.data_file = None
        self.volts_per_division = [3.3/(1<<15), 3.3/(1<<15)] # For signal [1,2]
        super().__init__(port, baudrate=115200)
        self.enter_raw_repl()
        self.exec('import photometry_upy')
        self.exec("p = photometry_upy.Photometry(mode='{}', pins={})".format(self.mode, pins))

    def set_sampling_rate(self, sampling_rate):
        self.sampling_rate = int(min(sampling_rate, self.max_rate))
        self.buffer_size = max(2, int(self.sampling_rate // 40) * 2)
        self.serial_chunk_size = (self.buffer_size+2)*2
        return self.sampling_rate

    def start(self):
        '''Start data aquistion and streaming on the pyboard.'''
        self.serial.reset_input_buffer()
        self.exec_raw_no_follow('p.start({},{})'.format(self.sampling_rate, self.buffer_size))

    def record(self, data_dir, subject_ID):
        '''Open data file and write data header.'''
        date_time = datetime.now()
        file_path = os.path.join(data_dir, subject_ID + 
                                 date_time.strftime('-%Y-%m-%d-%H%M%S') + '.ppd')
        self.data_file = open(file_path, 'wb')
        data_header = bytearray([0]*42)
        data_header[ 0:12] = subject_ID.ljust(12).encode()
        data_header[12:31] = date_time.isoformat(timespec='seconds').encode() # ISO 8601 format data time string
        data_header[31   ] = {'GCaMP/RFP':1, 'GCaMP/iso':2}[self.mode]
        data_header[32:34] = self.sampling_rate.to_bytes(2, 'little')
        data_header[34:38] = int(self.volts_per_division[0]*1e9).to_bytes(4, 'little')
        data_header[38:42] = int(self.volts_per_division[1]*1e9).to_bytes(4, 'little')
        self.data_file.write(len(data_header).to_bytes(2, 'little'))
        self.data_file.write(data_header)

    def stop_recording(self):
        if self.data_file:
            self.data_file.close()
        self.data_file = None

    def stop(self):
        self.serial.write(b'\r\x03\x03') # ctrl+c twice.
        if self.data_file:
            self.stop_recording()

    def process_data(self):
        '''Read a chunk of data from the serial line, extract signals and check end bytes.
        and check sum are correct.'''
        if self.serial.inWaiting() > (self.serial_chunk_size):
            chunk = np.frombuffer(self.serial.read(self.serial_chunk_size), dtype=np.dtype('<u2'))
            data = chunk[:-2]
            signal  = data >> 1        # Analog signal is most significant 15 bits.
            digital = (data % 2) == 1  # Digital signal is least significant bit.
            # Alternating samples are signals 1 and 2.
            signal_1 = signal[ ::2]
            signal_2 = signal[1::2]
            digital_1 = digital[ ::2]
            digital_2 = digital[1::2]
            if not chunk[-1] == 0: print('Bad end bytes')
            if not (sum(data) & 0xffff) == chunk[-2]: 
                print('Bad checksum')
                self.serial.reset_input_buffer()
            if self.data_file:
                self.data_file.write(data.tobytes())
            return signal_1, signal_2, digital_1, digital_2


# Import data -----------------------------------------------------------------------------

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
    signal_1 = signal[ ::2] * volts_per_division[0]
    signal_2 = signal[1::2] * volts_per_division[1]
    digital_1 = digital[ ::2]
    digital_2 = digital[1::2]    
    return {'subject_ID'   : subject_ID,
            'datetime'     : date_time,
            'datetime_str' : date_time.strftime('%Y-%m-%d %H:%M:%S'),
            'mode'         : mode,
            'sampling_rate': sampling_rate,
            'volts_per_div': volts_per_division,
            'signal_1'     : signal_1,
            'signal_2'     : signal_2,
            'digital_1'    : digital_1,
            'digital_2'    : digital_2}



