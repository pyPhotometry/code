import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from serial import SerialException
from photometry_host import Photometry_host

# Signal_history ------------------------------------------------------------

class Signal_history():
    # Class to store the history of a signal.

    def __init__(self, history_length):
        self.history = np.zeros(history_length)

    def update(self, new_data):
        # Store new data, ditch oldest data.
        data_len = len(new_data)
        self.history = np.roll(self.history, -data_len)
        self.history[-data_len:] = new_data

# Parameters ---------------------------------------------------------

history_dur = 5      # Duration of plotted signal history (seconds)

# Variables
#signal_1, signal_2, digital_1, digital_2 = [None, None, None, None]
board = None
mode  = 'GCaMP/iso'
port  = 'com23'
running = False

# Update -----------------------------------------------------------

def update():
    # Read data from the serial port and update the plot.
    global board, signal_1, signal_2, digital_1, digital_2, x
    if board:
        data = board.process_data()
        if data:
            new_signal_1, new_signal_2, new_digital_1, new_digital_2 = data
            new_signal_1 = new_signal_1 * 3.3 / (1 << 15)
            new_signal_2 = new_signal_2 * 3.3 / (1 << 15)
            signal_1.update(new_signal_1)
            signal_2.update(new_signal_2)
            digital_1.update(new_digital_1)
            digital_2.update(new_digital_2)
            analog_plot_1.setData(x, signal_1.history)
            analog_plot_2.setData(x, signal_2.history)
            digital_plot_1.setData(x, digital_1.history)
            digital_plot_2.setData(x, digital_2.history)
            sig_corr_plot.setData(signal_2.history, signal_1.history)
            QtGui.QApplication.processEvents()

# Button and box functions -------------------------------------------

def select_mode(selected_mode):
    global mode
    mode = selected_mode

def port_text_change(text):
    global port
    port = text

def connect():
    global port, board, signal_1, signal_2, digital_1, digital_2, x
    try:
        board = Photometry_host(port, mode=mode)
        # Setup variables to store data.
        history_length = int(board.sampling_rate*history_dur)
        x = np.linspace(-history_dur, 0, history_length)
        signal_1  = Signal_history(history_length)
        signal_2  = Signal_history(history_length)
        digital_1 = Signal_history(history_length) 
        digital_2 = Signal_history(history_length) 

        start_btn.setEnabled(True)
        connect_btn.setEnabled(False)
        mode_select.setEnabled(False)
        port_text.setText('Connected')
        port_text.setEnabled(False)
    except SerialException:
        port_text.setText('Connection failed')

def start():
    global board, running
    board.start()
    running = True
    start_btn.setEnabled(False)
    stop_btn.setEnabled(True)
    update_timer.start(50)

def stop():
    global board, running
    board.stop()
    running = False
    stop_btn.setEnabled(False)
    start_available_timer.start(500)

def start_available():
    start_btn.setEnabled(True)

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

mode_label = QtGui.QLabel("Mode:")
mode_select = QtGui.QComboBox()
mode_select.addItem('GCaMP/iso')
mode_select.addItem('GCaMP/RFP')
port_label = QtGui.QLabel("Serial port:")
port_text = QtGui.QLineEdit(port)
connect_btn = QtGui.QPushButton('Connect')
start_btn   = QtGui.QPushButton('Start')
stop_btn    = QtGui.QPushButton('Stop')
quit_btn    = QtGui.QPushButton('Quit')     

analog_axis  = pg.PlotWidget(title="Analog signal" , labels={'left':'Volts'})
digital_axis = pg.PlotWidget(title="Digital signal", labels={'left': 'Level', 'bottom':'Time (seconds)'})
sig_corr_axis  = pg.PlotWidget(title="Signal correlation" , labels={'left':'GCaMP', 'bottom':'control'})
ev_trig_axis = pg.PlotWidget(title="Event triggered average", labels={'left': 'Volts', 'bottom':'Time (seconds)'})

# Setup Axis.

analog_axis.addLegend()
analog_plot_1  = analog_axis.plot(pen=pg.mkPen('g'), name='GCaMP'  )
analog_plot_2  = analog_axis.plot(pen=pg.mkPen('r'), name='control')
digital_plot_1 = digital_axis.plot(pen=pg.mkPen('b'))
digital_plot_2 = digital_axis.plot(pen=pg.mkPen('y'))
sig_corr_plot  = sig_corr_axis.plot(pen=pg.mkPen(pg.hsvColor(0.5, sat=1.0, val=1.0, alpha=0.1)))

# analog_plot_1  = analog_axis.plot( x, signal_1.history , pen=pg.mkPen('g'), name='GCaMP'  )
# analog_plot_2  = analog_axis.plot( x, signal_1.history , pen=pg.mkPen('r'), name='control')
# digital_plot_1 = digital_axis.plot(x, digital_1.history, pen=pg.mkPen('b'))
# digital_plot_2 = digital_axis.plot(x, digital_2.history, pen=pg.mkPen('y'))
#sig_corr_plot  = sig_corr_axis.plot(signal_2.history, signal_1.history, 
#                                    pen=pg.mkPen(pg.hsvColor(0.5, sat=1.0, val=1.0, alpha=0.1)))
analog_axis.setYRange(0, 3.3, padding=0)
analog_axis.setXRange( -history_dur, history_dur*0.02, padding=0)
digital_axis.setYRange(-0.1, 1.1, padding=0)
digital_axis.setXRange(-history_dur, history_dur*0.02, padding=0)

## Create layout

vertical_layout     = QtGui.QVBoxLayout()
horizontal_layout_1 = QtGui.QHBoxLayout()
horizontal_layout_2 = QtGui.QHBoxLayout()

horizontal_layout_1.addWidget(mode_label)
horizontal_layout_1.addWidget(mode_select)
horizontal_layout_1.addWidget(port_label)
horizontal_layout_1.addWidget(port_text)
horizontal_layout_1.addWidget(connect_btn)
horizontal_layout_1.addWidget(start_btn)
horizontal_layout_1.addWidget(stop_btn)
horizontal_layout_1.addWidget(quit_btn)

horizontal_layout_2.addWidget(sig_corr_axis)
horizontal_layout_2.addWidget(ev_trig_axis)

vertical_layout.addLayout(horizontal_layout_1)
vertical_layout.addWidget(analog_axis,  40)
vertical_layout.addWidget(digital_axis, 20)
vertical_layout.addLayout(horizontal_layout_2, 30)

w.setLayout(vertical_layout)

# Connect widgets
mode_select.activated[str].connect(select_mode)
port_text.textChanged.connect(port_text_change)
connect_btn.clicked.connect(connect)
start_btn.clicked.connect(start)
stop_btn.clicked.connect(stop)
quit_btn.clicked.connect(quit)
start_btn.setEnabled(False)
stop_btn.setEnabled(False)

# Setup Timers.

update_timer = QtCore.QTimer() # Timer to regularly call update()
update_timer.timeout.connect(update)

start_available_timer = QtCore.QTimer() # Timer to make start button available with delay after stop.
start_available_timer.setSingleShot(True)
start_available_timer.timeout.connect(start_available)

# Start App.

w.show() 
app.exec_()