# Code that runs on the pyboard which handles data acquisition and streaming.

import pyb
import gc
from array import array

class Photometry():

    def __init__(self, mode, pins):
        assert mode in ['GCaMP/RFP', 'GCaMP/iso'], \
            "Invalid mode. Mode can be 'GCaMP/RFP' or 'GCaMP/iso'."
        self.mode = mode
        if mode == 'GCaMP/RFP': # 2 channel GFP/RFP acquisition mode.
            self.oversampling_rate = 3e5  # Hz.
        elif mode == 'GCaMP/iso': # GCaMP and isosbestic recorded on same channel using time division multiplexing.
            self.oversampling_rate = 64e3 # Hz.
        self.ADC1 = pyb.ADC(pins['ADC1'])
        self.ADC2 = pyb.ADC(pins['ADC2'])
        self.DI1 = pyb.Pin(pins['DI1'], pyb.Pin.IN, pyb.Pin.PULL_DOWN)
        self.DI2 = pyb.Pin(pins['DI2'], pyb.Pin.IN, pyb.Pin.PULL_DOWN)
        self.LED1 = pyb.Pin(pins['LED1'], pyb.Pin.OUT, value=False)
        self.LED2 = pyb.Pin(pins['LED2'], pyb.Pin.OUT, value=False)
        self.ovs_buffer = array('H',[0]*64) # Oversampling buffer
        self.ovs_timer = pyb.Timer(2)       # Oversampling timer.
        self.sampling_timer = pyb.Timer(3)
        self.usb_serial = pyb.USB_VCP()

    def start(self, sampling_rate, buffer_size):
        # Start acquisition, stream data to computer, wait for ctrl+c over serial to stop. 
        # Setup sample buffers.
        self.buffer_size = buffer_size
        self.sample_buffers = (array('H',[0]*(buffer_size+2)), array('H',[0]*(buffer_size+2)))
        self.buffer_data_mv = (memoryview(self.sample_buffers[0])[:-2], 
                               memoryview(self.sample_buffers[1])[:-2])      
        self.sample = 0  
        self.write_buf = 0 # Buffer to write data to.
        self.send_buf  = 1 # Buffer to send data from.
        self.write_ind = 0 # Buffer index to write new data to. 
        self.buffer_ready = False # Set to True when full buffer is ready to send.
        self.ovs_timer.init(freq=self.oversampling_rate)
        gc.disable()
        if self.mode == 'GCaMP/RFP':
            self.sampling_timer.init(freq=sampling_rate)
            self.sampling_timer.callback(self.gcamp_rfp_ISR)
        elif self.mode == 'GCaMP/iso':
            self.sampling_timer.init(freq=sampling_rate*2)
            self.sampling_timer.callback(self.gcamp_iso_ISR)
        try:
            while True:
                if self.buffer_ready:
                    self._send_buffer()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        # Stop aquisition
        self.sampling_timer.deinit()
        self.ovs_timer.deinit()
        gc.enable()

    @micropython.native
    def gcamp_rfp_ISR(self, t):
        # Interrupt service routine for GCamp/RFP acquisition mode, reads a sample from ADCs 
        # 1 and 2 sequentially, along with the two digital inputs. Analog signals are stored
        # in the 15 most significant bits of the sample buffer, digital signal in least
        # significant bit.
        self.ADC1.read_timed(self.ovs_buffer, self.ovs_timer)
        self.sample = sum(self.ovs_buffer) >> 3
        self.sample_buffers[self.write_buf][self.write_ind] = (self.sample << 1) | self.DI1.value()
        self.write_ind += 1
        self.ADC2.read_timed(self.ovs_buffer, self.ovs_timer)
        self.sample = sum(self.ovs_buffer) >> 3
        self.sample_buffers[self.write_buf][self.write_ind] = (self.sample << 1) | self.DI2.value()
        # Update write index and switch buffers if full.
        self.write_ind = (self.write_ind + 1) % self.buffer_size
        if self.write_ind == 0: # Buffer full, switch buffers.
            self.write_buf = 1 - self.write_buf
            self.send_buf  = 1 - self.send_buf
            self.buffer_ready = True

    @micropython.native
    def gcamp_iso_ISR(self, t):
        # Interrupt service routine for 2 channel GCamp / isosbestic acquisition mode.
        if self.write_ind % 2:   # Odd samples are isosbestic illumination.
            self.LED2.value(True) # Turn on 405nm illumination.
        else:                    # Even samples are blue illumination.
            self.LED1.value(True) # Turn on 470nm illumination.
        pyb.udelay(350)          # Wait before reading ADC (us).
        # Acquire sample and store in buffer.
        self.ADC1.read_timed(self.ovs_buffer, self.ovs_timer)
        self.sample = sum(self.ovs_buffer) >> 3
        if self.write_ind % 2:
            self.LED2.value(False) # Turn off 405nm illumination.
            self.sample_buffers[self.write_buf][self.write_ind] = (self.sample << 1) | self.DI2.value()
        else:
            self.LED1.value(False) # Turn on 470nm illumination.
            self.sample_buffers[self.write_buf][self.write_ind] = (self.sample << 1) | self.DI1.value()
        # Update write index and switch buffers if full.
        self.write_ind = (self.write_ind + 1) % self.buffer_size
        if self.write_ind == 0: # Buffer full, switch buffers.
            self.write_buf = 1 - self.write_buf
            self.send_buf  = 1 - self.send_buf
            self.buffer_ready = True

    @micropython.native
    def _send_buffer(self):
        # Send full buffer to host computer. Format of the serial chunks sent to the computer: 
        # buffer[:-2] = data, buffer[-2] = checksum, buffer[-1] = 0.
        self.sample_buffers[self.send_buf][-2] = sum(self.buffer_data_mv[self.send_buf]) # Checksum
        self.usb_serial.send(self.sample_buffers[self.send_buf])
        self.buffer_ready = False

