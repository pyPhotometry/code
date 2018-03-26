import numpy as np
import pylab as plt
from serial import SerialException
from pyboard import Pyboard, PyboardError

class Photometry_host(Pyboard):
    '''Class for aquiring data from a micropython photometry system on a host computer.'''

    def __init__(self, port, mode='GCaMP/iso'):
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
        super().__init__(port, baudrate=115200)
        self.enter_raw_repl()
        self.exec('import photometry')
        self.exec("p = photometry.Photometry(mode='{}')".format(self.mode))

    def set_sampling_rate(self, sampling_rate):
        self.sampling_rate = int(min(sampling_rate, self.max_rate))
        #self.buffer_size = max(2, int(np.ceil(self.sampling_rate / 40) * 2)) # Size of alternating signal buffers on pyboard.
        self.buffer_size = max(2, int(self.sampling_rate // 40) * 2)
        self.serial_chunk_size = (self.buffer_size+2)*2
        return self.sampling_rate

    def start(self):
        '''Start data aquistion and streaming on the pyboard.'''
        self.serial.reset_input_buffer()
        self.exec_raw_no_follow('p.start({},{})'.format(self.sampling_rate, self.buffer_size))

    def record(self, file_path):
        self.data_file = open(file_path, 'wb')

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
            chunk = np.frombuffer(self.serial.read(self.serial_chunk_size), dtype=np.uint16)
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
            if self.data_file:
                self.data_file.write(data.tobytes())
            return signal_1, signal_2, digital_1, digital_2