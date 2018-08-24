# Code which runs on host computer and implements communication with pyboard.
import os
import numpy as np
import json
from datetime import datetime
from time import sleep

try:
    import pyperclip
except ImportError:
    pyperclip = None

from pyboard import Pyboard

VERSION = 0.1 # Version number of pyPhotometry.

class Photometry_host(Pyboard):
    '''Class for aquiring data from a micropython photometry system on a host computer.'''

    def __init__(self, port):
        '''Open connection to pyboard and instantiate Photometry class on pyboard with
        provided parameters.'''
        self.data_file = None
        self.volts_per_division = [3.3/(1<<15), 3.3/(1<<15)] # For signal [1,2]
        self.running = False
        super().__init__(port, baudrate=115200)
 
    def set_mode(self, mode):
        # Set control channel mode.
        assert mode in ['GCaMP/RFP', 'GCaMP/iso', 'GCaMP/RFP_dif'], \
            "Invalid mode, value values: 'GCaMP/RFP', 'GCaMP/iso' or 'GCaMP/RFP_dif'."
        self.mode = mode
        if mode == 'GCaMP/RFP':   # 2 channel GFP/RFP acquisition mode.
            self.max_rate = 1000  # Maximum sampling rate allowed for this mode.
        elif mode in ('GCaMP/iso', 'GCaMP/RFP_dif'): # GCaMP and isosbestic using time division multiplexing.
            self.max_rate = 200   # Hz.
        self.set_sampling_rate(self.max_rate)
        self.enter_raw_repl() # Reset pyboard.
        self.exec('import photometry_upy') 
        self.exec("p = photometry_upy.Photometry(mode='{}')".format(self.mode))        

    def set_LED_current(self, LED_1_current=None, LED_2_current=None):
        if self.running:
            if LED_1_current:
                self.serial.write(b'\xFD' + LED_1_current.to_bytes(1, 'little'))
            if LED_2_current:
                self.serial.write(b'\xFE' + LED_2_current.to_bytes(1, 'little'))
        else:
            self.exec('p.set_LED_current({},{})'.format(LED_1_current, LED_2_current))

    def set_sampling_rate(self, sampling_rate):
        self.sampling_rate = int(min(sampling_rate, self.max_rate))
        self.buffer_size = max(2, int(self.sampling_rate // 40) * 2)
        self.serial_chunk_size = (self.buffer_size+2)*2
        return self.sampling_rate

    def start(self):
        '''Start data aquistion and streaming on the pyboard.'''
        self.exec_raw_no_follow('p.start({},{})'.format(self.sampling_rate, self.buffer_size))
        self.running = True

    def record(self, data_dir, subject_ID):
        '''Open data file and write data header.'''
        date_time = datetime.now()
        file_name = subject_ID + date_time.strftime('-%Y-%m-%d-%H%M%S') + '.ppd'
        file_path = os.path.join(data_dir, file_name)
        if pyperclip: pyperclip.copy(file_name)
        self.data_file = open(file_path, 'wb')
        header_dict = {'subject_ID': subject_ID,
                       'date_time' : date_time.isoformat(timespec='seconds'),
                       'mode': self.mode,
                       'sampling_rate': self.sampling_rate,
                       'volts_per_division': self.volts_per_division,
                       'version': VERSION}
        data_header = json.dumps(header_dict).encode()
        self.data_file.write(len(data_header).to_bytes(2, 'little'))
        self.data_file.write(data_header)

    def stop_recording(self):
        if self.data_file:
            self.data_file.close()
        self.data_file = None

    def stop(self):
        if self.data_file:
            self.stop_recording()
        self.serial.write(b'\xFF') # Stop signal
        sleep(0.1)
        self.serial.reset_input_buffer()
        self.running = False

    def process_data(self):
        '''Read a chunk of data from the serial line, extract signals and check end bytes.
        and check sum are correct.'''
        if self.serial.in_waiting > (self.serial_chunk_size):
            chunk = np.frombuffer(self.serial.read(self.serial_chunk_size), dtype=np.dtype('<u2'))
            data = chunk[:-2]
            signal  = data >> 1        # Analog signal is most significant 15 bits.
            digital = (data % 2) == 1  # Digital signal is least significant bit.
            # Alternating samples are signals 1 and 2.
            ADC1 = signal[ ::2]
            ADC2 = signal[1::2]
            DI1 = digital[ ::2]
            DI2 = digital[1::2]
            if not chunk[-1] == 0:
                print('Bad end bytes')
            if not (sum(data) & 0xffff) == chunk[-2]: 
                print('Bad checksum')
                self.serial.reset_input_buffer()
            if self.data_file:
                self.data_file.write(data.tobytes())
            return ADC1, ADC2, DI1, DI2