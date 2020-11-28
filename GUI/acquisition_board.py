# Code which runs on host computer and implements communication with pyboard and saving 
# data to disk.  
# Copyright (c) Thomas Akam 2018-2020.  Licenced under the GNU General Public License v3.

import os
import numpy as np
import json
import time
from inspect import getsource
from datetime import datetime
from time import sleep

from GUI.pyboard import Pyboard, PyboardError
from GUI.config import VERSION

class Acquisition_board(Pyboard):
    '''Class for aquiring data from a micropython photometry system on a host computer.'''

    def __init__(self, port):
        '''Open connection to pyboard and instantiate Photometry class on pyboard with
        provided parameters.'''
        self.data_file = None
        self.running = False
        self.LED_current = [0,0]
        self.file_type = None
        super().__init__(port, baudrate=115200)
        self.enter_raw_repl() # Reset pyboard.
        # Transfer firmware if not already on board.
        self.exec(getsource(_djb2_file))     # Define djb2 hashing function on board.
        self.exec(getsource(_receive_file))  # Define recieve file function on board.
        self.transfer_file(os.path.join('uPy', 'photometry_upy.py'))
        # Import firmware and instantiate photometry class.
        self.exec('import photometry_upy')
        self.exec('p = photometry_upy.Photometry()')
        self.volts_per_division = eval(self.eval('p.volts_per_division').decode())
 
    # -----------------------------------------------------------------------
    # Data acquisition.
    # -----------------------------------------------------------------------

    def set_mode(self, mode):
        # Set control channel mode.
        assert mode in ['2 colour continuous', '1 colour time div.', '2 colour time div.'], \
            "Invalid mode, value values: '2 colour continuous', '1 colour time div.' or '2 colour time div.'."
        self.mode = mode
        if mode == '2 colour continuous':   # 2 channel GFP/RFP acquisition mode.
            self.max_rate = 1000  # Maximum sampling rate allowed for this mode.
        elif mode in ('1 colour time div.', '2 colour time div.'): # GCaMP and isosbestic using time division multiplexing.
            self.max_rate = 130   # Hz.
        self.set_sampling_rate(self.max_rate)
        self.exec("p.set_mode('{}')".format(mode))

    def set_LED_current(self, LED_1_current=None, LED_2_current=None):
        if LED_1_current is not None:   
            self.LED_current[0] = LED_1_current
        if LED_2_current is not None:   
            self.LED_current[1] = LED_2_current
        if self.running:
            if LED_1_current is not None:
                self.serial.write(b'\xFD' + LED_1_current.to_bytes(1, 'little'))
            if LED_2_current is not None:
                self.serial.write(b'\xFE' + LED_2_current.to_bytes(1, 'little'))
        else:
            self.exec('p.set_LED_current({},{})'.format(LED_1_current, LED_2_current))

    def set_sampling_rate(self, sampling_rate):
        self.sampling_rate = int(min(sampling_rate, self.max_rate))
        self.buffer_size = max(2, int(self.sampling_rate // 40) * 2)
        self.serial_chunk_size = (self.buffer_size+3)*2
        return self.sampling_rate

    def start(self):
        '''Start data aquistion and streaming on the pyboard.'''
        self.exec_raw_no_follow('p.start({},{})'.format(self.sampling_rate, self.buffer_size))
        self.chunk_number = 0 # Number of data chunks recieved from board, modulo 2**16.
        self.running = True

    def record(self, data_dir, subject_ID, file_type='ppd'):
        '''Open data file and write data header.'''
        assert file_type in ['csv', 'ppd'], 'Invalid file type'
        self.file_type = file_type
        date_time = datetime.now()
        file_name = subject_ID + date_time.strftime('-%Y-%m-%d-%H%M%S') + '.' + file_type
        file_path = os.path.join(data_dir, file_name)
        header_dict = {'subject_ID': subject_ID,
                       'date_time' : date_time.isoformat(timespec='seconds'),
                       'mode': self.mode,
                       'sampling_rate': self.sampling_rate,
                       'volts_per_division': self.volts_per_division,
                       'LED_current': self.LED_current,
                       'version': VERSION}
        if file_type == 'ppd': # Single binary .ppd file.
            self.data_file = open(file_path, 'wb')
            data_header = json.dumps(header_dict).encode()
            self.data_file.write(len(data_header).to_bytes(2, 'little'))
            self.data_file.write(data_header)
        elif file_type == 'csv': # Header in .json file and data in .csv file.
            with open(os.path.join(data_dir, file_name[:-4] + '.json'), 'w') as headerfile:
                headerfile.write(json.dumps(header_dict, sort_keys=True, indent=4))
            self.data_file = open(file_path, 'w')
            self.data_file.write('Analog1, Analog2, Digital1, Digital2\n')
        return file_name

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
        '''Read a chunk of data from the serial line, check data integrity, extract signals,
        save signals to disk if file is open, return signals.'''
        if self.serial.in_waiting > (self.serial_chunk_size):
            chunk = np.frombuffer(self.serial.read(self.serial_chunk_size), dtype=np.dtype('<u2'))
            data = chunk[:-3]
            checksum_OK  = chunk[-2] == (sum(data) & 0xffff)
            end_bytes_OK = chunk[-1] == 0
            if not checksum_OK:
                print('Bad checksum')
            if not end_bytes_OK:
                print('Bad end bytes')
            if not checksum_OK and not end_bytes_OK:
                # Chunk read by computer not aligned with that send by board.
                self.serial.reset_input_buffer()
            else:
                # check whether any chunks have been skipped, this can occur following an input buffer reset.
                self.chunk_number = (self.chunk_number + 1) & 0xffff
                n_skipped_chunks = np.int16(chunk[-3] - self.chunk_number) # rollover safe subtraction.
                if not n_skipped_chunks == 0:
                    print(f'skipped chunks:{n_skipped_chunks}')
                if n_skipped_chunks > 0: # Prepend data with zeros to replace skipped chunks.
                    skip_pad = np.zeros(self.buffer_size*n_skipped_chunks, dtype=np.dtype('<u2'))
                    data = np.hstack([skip_pad, data])
                    self.chunk_number = (self.chunk_number + n_skipped_chunks) & 0xffff
                # Extract signals.
                signal  = data >> 1        # Analog signal is most significant 15 bits.
                digital = (data % 2) == 1  # Digital signal is least significant bit.
                ADC1 = signal[ ::2]        # Alternating samples are signals 1 and 2.
                ADC2 = signal[1::2]
                DI1 = digital[ ::2]
                DI2 = digital[1::2]
                # Write data to disk.
                if self.data_file:
                    if self.file_type == 'ppd': # Binary data file.
                        self.data_file.write(data.tobytes())
                    else: # CSV data file.
                        np.savetxt(self.data_file, np.array([ADC1,ADC2,DI1,DI2], dtype=int).T, 
                                   fmt='%d', delimiter=',')
                return ADC1, ADC2, DI1, DI2

    # -----------------------------------------------------------------------
    # File transfer
    # -----------------------------------------------------------------------

    def get_file_hash(self, target_path):
        '''Get the djb2 hash of a file on the pyboard.'''
        try:
            file_hash = int(self.eval("_djb2_file('{}')".format(target_path)).decode())
        except PyboardError: # File does not exist.
            return -1  
        return file_hash

    def transfer_file(self, file_path):
        '''Copy file at file_path to pyboard.'''
        target_path = os.path.split(file_path)[-1]
        file_size = os.path.getsize(file_path)
        file_hash = _djb2_file(file_path)
        # Try to load file, return once file hash on board matches that on computer.
        for i in range(10):
            if file_hash == self.get_file_hash(target_path):
                return
            self.exec_raw_no_follow("_receive_file('{}',{})"
                                    .format(target_path, file_size))
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    self.serial.write(chunk)
                    response_bytes = self.serial.read(2)
                    if response_bytes != b'OK':
                        time.sleep(0.01)
                        self.serial.reset_input_buffer()
                        raise PyboardError
                self.follow(3)
        # Unable to transfer file.
        raise PyboardError

# ----------------------------------------------------------------------------------------
#  Helper functions.
# ----------------------------------------------------------------------------------------

# djb2 hashing algorithm used to check integrity of transfered files.
def _djb2_file(file_path):
    with open(file_path, 'rb') as f:
        h = 5381
        while True:
            c = f.read(4)
            if not c:
                break
            h = ((h << 5) + h + int.from_bytes(c,'little')) & 0xFFFFFFFF           
    return h

# Used on pyboard for file transfer.
def _receive_file(file_path, file_size):
    usb = pyb.USB_VCP()
    usb.setinterrupt(-1)
    buf_size = 512
    buf = bytearray(buf_size)
    buf_mv = memoryview(buf)
    bytes_remaining = file_size
    try:
        with open(file_path, 'wb') as f:
            while bytes_remaining > 0:
                bytes_read = usb.recv(buf, timeout=5)
                usb.write(b'OK')
                if bytes_read:
                    bytes_remaining -= bytes_read
                    f.write(buf_mv[:bytes_read])
    except:
        usb.write(b'ER')