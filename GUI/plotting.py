import numpy as np
import pyqtgraph as pg
from datetime import timedelta, datetime
from pyqtgraph.Qt import QtGui, QtCore

from config import history_dur, triggered_dur

# Analog_plot ------------------------------------------------------

class Analog_plot():

    def __init__(self):
        self.axis = pg.PlotWidget(title="Analog signal" , labels={'left':'Volts'})
        self.legend = self.axis.addLegend(offset=(10, 10))
        self.plot_1  = self.axis.plot(pen=pg.mkPen('g'), name='GCaMP'  )
        self.plot_2  = self.axis.plot(pen=pg.mkPen('r'), name='control')
        self.axis.setYRange(0, 3.3, padding=0)
        self.axis.setXRange( -history_dur, history_dur*0.02, padding=0)

    def reset(self, sampling_rate):
        history_length = int(sampling_rate*history_dur)
        self.ADC1  = Signal_history(history_length)
        self.ADC2  = Signal_history(history_length)
        self.x = np.linspace(-history_dur, 0, history_length) # X axis for timeseries plots.

    def update(self, new_ADC1, new_ADC2):
            new_ADC1 = 3.3 * new_ADC1 / (1 << 15) # Convert to Volts.
            new_ADC2 = 3.3 * new_ADC2 / (1 << 15)
            self.ADC1.update(new_ADC1)
            self.ADC2.update(new_ADC2)
            self.plot_1.setData(self.x, self.ADC1.history)
            self.plot_2.setData(self.x, self.ADC2.history)

# Digital_plot ------------------------------------------------------

class Digital_plot():

    def __init__(self):
        self.axis = pg.PlotWidget(title="Digital signal", labels={'left': 'Level', 'bottom':'Time (seconds)'})
        self.axis.addLegend(offset=(10, 10))
        self.plot_1 = self.axis.plot(pen=pg.mkPen('b'), name='digital 1')
        self.plot_2 = self.axis.plot(pen=pg.mkPen('y'), name='digital 2')
        self.axis.setYRange(-0.1, 1.1, padding=0)
        self.axis.setXRange(-history_dur, history_dur*0.02, padding=0)

    def reset(self, sampling_rate):
        history_length = int(sampling_rate*history_dur)
        self.DI1 = Signal_history(history_length, int) 
        self.DI2 = Signal_history(history_length, int)
        self.x = np.linspace(-history_dur, 0, history_length) # X axis for timeseries plots.

    def update(self, new_DI1, new_DI2):
            self.DI1.update(new_DI1)
            self.DI2.update(new_DI2)
            self.plot_1.setData(self.x, self.DI1.history)
            self.plot_2.setData(self.x, self.DI2.history)
 
# Event triggered plot -------------------------------------------------

class Event_triggered_plot():

    def __init__(self):
        self.axis = pg.PlotWidget(title="Event triggered", labels={'left': 'Volts', 'bottom':'Time (seconds)'})
        self.axis.addLegend(offset=(-10, 10))
        self.prev_plot = self.axis.plot(pen=pg.mkPen(pg.hsvColor(0.6, sat=0, alpha=0.3)), name='latest')
        self.ave_plot  = self.axis.plot(pen=pg.mkPen(pg.hsvColor(0.6)), name='average')
        self.axis.addItem(pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(style=QtCore.Qt.DotLine)))
        self.axis.setXRange(triggered_dur[0], triggered_dur[1], padding=0)


    def reset(self, sampling_rate):
        self.window = (np.array(triggered_dur)*sampling_rate).astype(int)   # Window for event triggered signals (samples [pre, post])
        self.x = np.linspace(*triggered_dur, self.window[1]-self.window[0]) # X axis for event triggered plots.
        self.average = None
        self.prev_plot.clear()
        self.ave_plot.clear()

    def update(self, new_DI1, digital, analog):
        # Update event triggered average plot.
        new_data_len = len(new_DI1)
        trig_section = digital.DI1.history[-self.window[1]-new_data_len-1:-self.window[1]]
        rising_edges = np.where(np.diff(trig_section)==1)[0]
        for i, edge in enumerate(rising_edges):
            edge_ind = -self.window[1]-new_data_len-1+edge # Position of edge in signal history.
            ev_trig_sig = analog.ADC1.history[edge_ind+self.window[0]:edge_ind+self.window[1]]
            if self.average is None: # First acquisition
                self.average = ev_trig_sig
            else: # Update averaged trace.
                self.average = 0.8*self.average + 0.2*ev_trig_sig
            if i+1 == len(rising_edges): 
                self.prev_plot.setData(self.x, ev_trig_sig)
                self.ave_plot.setData(self.x, self.average)

 # Signal_history ------------------------------------------------------------

class Signal_history():
    # Buffer to store the recent history of a signal.

    def __init__(self, history_length, dtype=float):
        self.history = np.zeros(history_length, dtype)

    def update(self, new_data):
        # Move old data along buffer, store new data samples.
        data_len = len(new_data)
        self.history = np.roll(self.history, -data_len)
        self.history[-data_len:] = new_data

# Record_clock ----------------------------------------------------

class Record_clock():
    # Class for displaying the run time.

    def __init__(self, axis):
        self.clock_text = pg.TextItem(text='')
        self.clock_text.setFont(QtGui.QFont('arial',12, QtGui.QFont.Bold))
        axis.getViewBox().addItem(self.clock_text, ignoreBounds=True)
        self.clock_text.setParentItem(axis.getViewBox())
        self.clock_text.setPos(190,10)
        self.recording_text = pg.TextItem(text='', color=(255,0,0))
        self.recording_text.setFont(QtGui.QFont('arial',12,QtGui.QFont.Bold))
        axis.getViewBox().addItem(self.recording_text, ignoreBounds=True)
        self.recording_text.setParentItem(axis.getViewBox())
        self.recording_text.setPos(100,10)
        self.start_time = None

    def start(self):
        self.start_time = datetime.now()
        self.recording_text.setText('Recording')

    def update(self):
        if self.start_time:
            self.clock_text.setText(str(datetime.now()-self.start_time)[:7])

    def stop(self):
        self.clock_text.setText('')
        self.recording_text.setText('')
        self.start_time = None






