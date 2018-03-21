import numpy as np
import pylab as plt
from serial import SerialException
from pyboard import Pyboard, PyboardError

class Photometry_host(Pyboard):
    '''Class for aquiring data from a micropython photometry system on a host computer.'''

    def __init__(self, port, buffer_size=256, sampling_rate=256):
        '''Open connection to pyboard and instantiate Photometry class on pyboard with
        provided parameters.'''
        self.buffer_size   = buffer_size
        self.sampling_rate = sampling_rate
        self.chunk_n_bytes = (buffer_size+2)*2

        super().__init__(port, baudrate=115200)
        self.enter_raw_repl()
        self.exec('import photometry')

        self.exec('p = photometry.Photometry(sampling_rate={}, buffer_size={})'
                  .format(sampling_rate, buffer_size))

    def start(self):
        '''Start data aquistion and streaming on the pyboard.'''
        self.serial.reset_input_buffer()
        self.exec_raw_no_follow('p.run()')

    def stop(self):
        self.serial.write(b'\r\x03\x03') # ctrl+c twice.

    def process_data(self):
        '''Read a chunk of data from the serial line, extract signals and check end bytes.
        and check sum are correct.'''
        if self.serial.inWaiting() > (self.chunk_n_bytes):
            chunk = np.frombuffer(self.serial.read(self.chunk_n_bytes), dtype=np.uint16)
            data = chunk[:-2]
            signal  = data & 0x7fff # Analog signal is least significant 15 bits.
            digital = data > 0x7fff # Digital signal is most significant bit.
            # Alternating samples are signals 1 and 2.
            signal_1 = signal[ ::2]
            signal_2 = signal[1::2]
            digital_1 = digital[ ::2]
            digital_2 = digital[1::2]
            if not chunk[-1] == 0: print('Bad end bytes')
            if not (sum(data) & 0xffff) == chunk[-2]: 
                print('Bad checksum')
                self.serial.reset_input_buffer()
            return signal_1, signal_2, digital_1, digital_2