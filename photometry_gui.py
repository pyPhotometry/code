import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from serial import SerialException
from sklearn.linear_model import LinearRegression
from photometry_host import Photometry_host

# Signal_history ------------------------------------------------------------

class Signal_history():
    # Buffer to store the recent history of a signal.

    def __init__(self, history_length, dtype=float):
        self.history = np.zeros(history_length, dtype)

    def update(self, new_data):
        # Store new data samples, ditch oldest data.
        data_len = len(new_data)
        self.history = np.roll(self.history, -data_len)
        self.history[-data_len:] = new_data

# Parameters ---------------------------------------------------------

history_dur = 5            # Duration of plotted signal history (seconds)
trig_window_dur = [-0.5,3] # Window duration for event triggered signals (seconds [pre, post])

# Variables
board = None
mode  = 'GCaMP/iso'
port  = 'com23'
running = False
OLS = LinearRegression()
ev_trig_ave = None # Event triggered average.

# Update -----------------------------------------------------------

def update():
    # Read data from the serial port and update the plot.
    global board, signal_1, signal_2, digital_1, digital_2, x, x_et, ev_trig_ave
    if board:
        data = board.process_data()
        if data:
            new_signal_1, new_signal_2, new_digital_1, new_digital_2 = data
            new_signal_1 = new_signal_1 * 3.3 / (1 << 15)
            new_signal_2 = new_signal_2 * 3.3 / (1 << 15)
            # Update signal buffers.
            signal_1.update(new_signal_1)
            signal_2.update(new_signal_2)
            digital_1.update(new_digital_1)
            digital_2.update(new_digital_2)
            # Update signal timeseries plots.
            analog_plot_1.setData(x, signal_1.history)
            analog_plot_2.setData(x, signal_2.history)
            digital_plot_1.setData(x, digital_1.history)
            digital_plot_2.setData(x, digital_2.history)
            # Update signal correlation plot.
            sig_corr_plot.setData(signal_2.history, signal_1.history)
            OLS.fit(signal_2.history[:,None], signal_1.history[:,None])
            x_c = np.array([np.min(signal_2.history), np.max(signal_2.history)])
            y_c = OLS.predict(x_c[:,None]).flatten()
            reg_fit_plot.setData(x_c, y_c)
            sig_corr_axis.setTitle('Signal correlation, slope = {:.3f}'.format(OLS.coef_[0][0]))
            # Update event triggered average plot.
            new_data_len = len(new_digital_1)
            trig_section = digital_1.history[-trig_window[1]-new_data_len-1:-trig_window[1]]
            rising_edges = np.where(np.diff(trig_section)==1)[0]
            for i, edge in enumerate(rising_edges):
                edge_ind = -trig_window[1]-new_data_len-1+edge # Position of edge in signal history.
                ev_trig_sig = signal_1.history[edge_ind+trig_window[0]:edge_ind+trig_window[1]]
                if ev_trig_ave is None: # First acquisition
                    ev_trig_ave = ev_trig_sig
                else: # Update averaged trace.
                    ev_trig_ave = 0.8*ev_trig_ave + 0.2*ev_trig_sig
                if i+1 == len(rising_edges): 
                    ev_trig_plot.setData(x_et, ev_trig_sig)
                    ev_ave_plot.setData(x_et, ev_trig_ave)

# Button and box functions -------------------------------------------

def select_mode(selected_mode):
    global mode
    mode = selected_mode

def port_text_change(text):
    global port
    port = text

def connect():
    global port, board, signal_1, signal_2, digital_1, digital_2, x, x_et, trig_window
    try:
        board = Photometry_host(port, mode=mode)
        # Setup variables.
        history_length = int(board.sampling_rate*history_dur)
        x = np.linspace(-history_dur, 0, history_length) # X axis for timeseries plots.
        trig_window = (np.array(trig_window_dur)*board.sampling_rate).astype(int) # Window duration for event triggered signals (samples [pre, post])
        x_et = np.linspace(*trig_window_dur, trig_window[1]-trig_window[0]) # X axis for event triggered plots.
        # Instantiate signal buffers.
        signal_1  = Signal_history(history_length)
        signal_2  = Signal_history(history_length)
        digital_1 = Signal_history(history_length, int) 
        digital_2 = Signal_history(history_length, int)
        # Update UI.
        start_button.setEnabled(True)
        connect_button.setEnabled(False)
        mode_select.setEnabled(False)
        status_text.setText('Connected')
        port_text.setEnabled(False)
    except SerialException:
        status_text.setText('Connection failed')

def start():
    global board, running
    update_timer.start(10)
    board.start()
    running = True
    start_button.setEnabled(False)
    stop_button.setEnabled(True)
    status_text.setText('Runnig')
    subject_text.setEnabled(False)

def stop():
    global board, running
    update_timer.stop()
    board.stop()
    running = False
    stop_button.setEnabled(False)
    start_available_timer.start(500)
    status_text.setText('Connected')

def start_available():
    start_button.setEnabled(True)

def quit():
    global board, running
    if running: stop()
    if board: board.close()
    QtCore.QCoreApplication.instance().quit()

# Main  -----------------------------------------------------------

app = QtGui.QApplication([])  # Start QT

## Create widgets.

w = QtGui.QWidget()
w.setWindowTitle('Photometry GUI')
status_label = QtGui.QLabel("Status:")
status_text = QtGui.QLineEdit('Not connected')
status_text.setStyleSheet('background-color:rgb(210, 210, 210);')
status_text.setReadOnly(True)
mode_label = QtGui.QLabel("Mode:")
mode_select = QtGui.QComboBox()
mode_select.addItem('GCaMP/iso')
mode_select.addItem('GCaMP/RFP')
port_label = QtGui.QLabel("Serial port:")
port_text = QtGui.QLineEdit(port)
subject_label = QtGui.QLabel("Subject ID:")
subject_text = QtGui.QLineEdit()
connect_button = QtGui.QPushButton('Connect')
start_button = QtGui.QPushButton('Start')
record_button= QtGui.QPushButton('Record')
stop_button = QtGui.QPushButton('Stop')
quit_button = QtGui.QPushButton('Quit')     

analog_axis  = pg.PlotWidget(title="Analog signal" , labels={'left':'Volts'})
digital_axis = pg.PlotWidget(title="Digital signal", labels={'left': 'Level', 'bottom':'Time (seconds)'})
sig_corr_axis  = pg.PlotWidget(title="Signal correlation" , labels={'left':'GCaMP', 'bottom':'control'})
ev_trig_axis = pg.PlotWidget(title="Event triggered", labels={'left': 'Volts', 'bottom':'Time (seconds)'})

# Setup Axis.

analog_axis.addLegend(offset=(10, 10))
analog_plot_1  = analog_axis.plot(pen=pg.mkPen('g'), name='GCaMP'  )
analog_plot_2  = analog_axis.plot(pen=pg.mkPen('r'), name='control')
analog_axis.setYRange(0, 3.3, padding=0)
analog_axis.setXRange( -history_dur, history_dur*0.02, padding=0)

digital_plot_1 = digital_axis.plot(pen=pg.mkPen('b'))
digital_plot_2 = digital_axis.plot(pen=pg.mkPen('y'))
digital_axis.setYRange(-0.1, 1.1, padding=0)
digital_axis.setXRange(-history_dur, history_dur*0.02, padding=0)

sig_corr_plot  = sig_corr_axis.plot(pen=pg.mkPen(pg.hsvColor(0.5, alpha=0.1)))
reg_fit_plot = sig_corr_axis.plot(pen=pg.mkPen(style=QtCore.Qt.DashLine))

ev_trig_axis.addLegend(offset=(-10, 10))
ev_trig_plot = ev_trig_axis.plot(pen=pg.mkPen(pg.hsvColor(0.6, sat=0, alpha=0.3)), name='latest')
ev_ave_plot  = ev_trig_axis.plot(pen=pg.mkPen(pg.hsvColor(0.6)), name='average')
ev_trig_axis.addItem(pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(style=QtCore.Qt.DotLine)))
ev_trig_axis.setXRange(trig_window_dur[0], trig_window_dur[1], padding=0)

## Create layout

vertical_layout     = QtGui.QVBoxLayout()
horizontal_layout_1 = QtGui.QHBoxLayout()
horizontal_layout_2 = QtGui.QHBoxLayout()

horizontal_layout_1.addWidget(status_label)
horizontal_layout_1.addWidget(status_text)
horizontal_layout_1.addWidget(mode_label)
horizontal_layout_1.addWidget(mode_select)
horizontal_layout_1.addWidget(port_label)
horizontal_layout_1.addWidget(port_text)
horizontal_layout_1.addWidget(subject_label)
horizontal_layout_1.addWidget(subject_text)
horizontal_layout_1.addWidget(connect_button)
horizontal_layout_1.addWidget(start_button)
horizontal_layout_1.addWidget(record_button)
horizontal_layout_1.addWidget(stop_button)
horizontal_layout_1.addWidget(quit_button)

horizontal_layout_2.addWidget(sig_corr_axis)
horizontal_layout_2.addWidget(ev_trig_axis)

vertical_layout.addLayout(horizontal_layout_1)
vertical_layout.addWidget(analog_axis,  50)
vertical_layout.addWidget(digital_axis, 15)
vertical_layout.addLayout(horizontal_layout_2, 30)

w.setLayout(vertical_layout)

# Connect widgets
mode_select.activated[str].connect(select_mode)
port_text.textChanged.connect(port_text_change)
connect_button.clicked.connect(connect)
start_button.clicked.connect(start)
stop_button.clicked.connect(stop)
quit_button.clicked.connect(quit)
start_button.setEnabled(False)
record_button.setEnabled(False)
stop_button.setEnabled(False)

# Setup Timers.

update_timer = QtCore.QTimer() # Timer to regularly call update()
update_timer.timeout.connect(update)

start_available_timer = QtCore.QTimer() # Timer to make start button available with delay after stop.
start_available_timer.setSingleShot(True)
start_available_timer.timeout.connect(start_available)

# Start App.

w.show() 
app.exec_()