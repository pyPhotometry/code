import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from sklearn.linear_model import LinearRegression

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

        self.recording = pg.TextItem(text='', color=(255,0,0))
        self.recording.setFont(QtGui.QFont('arial',16,QtGui.QFont.Bold))
        self.axis.addItem(self.recording, ignoreBounds=True)
        self.recording.setParentItem(self.axis.getViewBox())
        self.recording.setPos(100,10)

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

# Correlation plot -------------------------------------------------

class Correlation_plot():

    def __init__(self):
        self.axis  = pg.PlotWidget(title="Signal correlation" , labels={'left':'GCaMP', 'bottom':'control'})
        self.corr_plot = self.axis.plot(pen=pg.mkPen(pg.hsvColor(0.5, alpha=0.1)))
        self.reg_fit_plot = self.axis.plot(pen=pg.mkPen(style=QtCore.Qt.DashLine))
        self.OLS = LinearRegression()

    def reset(self, sampling_rate):
        history_length = int(sampling_rate*history_dur)
        self.DI1 = Signal_history(history_length, int) 
        self.DI2 = Signal_history(history_length, int)
        self.x = np.linspace(-history_dur, 0, history_length) # X axis for timeseries plots.

    def update(self, analog):
        self.corr_plot.setData(analog.ADC2.history, analog.ADC1.history)
        self.OLS.fit(analog.ADC2.history[:,None], analog.ADC1.history[:,None])
        x_c = np.array([np.min(analog.ADC2.history), np.max(analog.ADC2.history)])
        y_c = self.OLS.predict(x_c[:,None]).flatten()
        self.reg_fit_plot.setData(x_c, y_c)
        self.axis.setTitle('Signal correlation, slope = {:.3f}'.format(self.OLS.coef_[0][0]))
 
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
