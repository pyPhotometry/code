import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from serial import SerialException
from photometry_host import Photometry_host

# Parameters

buffer_size = 25
sampling_rate = 1000   # Hz
history_dur = 5        # Duration of plotted signal history (seconds)

# Variables

history_length = int(sampling_rate*history_dur)
x = np.linspace(-history_dur, 0, history_length)
signal  = np.zeros(history_length)
digital = np.zeros(history_length)    
board = None
port  = 'com23'
running = False


# Update -----------------------------------------------------------

def update():
    # Read data from the serial port and update the plot.
    global analog_plot, signal, digital, board
    if board:
        data = board.process_data()
        if data:
            new_signal, new_digital = data
            new_signal = new_signal * 3.3 / (1 << 15)
            signal = np.roll(signal, -board.buffer_size)
            signal[-board.buffer_size:] = new_signal
            digital = np.roll(digital, -board.buffer_size)
            digital[-board.buffer_size:] = new_digital
            analog_plot.setData(x, signal)
            digital_plot.setData(x, digital)
            QtGui.QApplication.processEvents()

# Button and box functions -------------------------------------------

def port_text_change(text):
    global port
    port = text

def connect():
    global port, board
    try:
        board = Photometry_host(port, buffer_size=buffer_size, sampling_rate=sampling_rate)
        start_btn.setEnabled(True)
        connect_btn.setEnabled(False)
        port_text.setText('Connected')
    except SerialException:
        port_text.setText('Connection failed')

def start():
    global board, running
    board.start()
    running = True
    start_btn.setEnabled(False)
    stop_btn.setEnabled(True)

def stop():
    global board, running
    board.stop()
    running = False
    start_btn.setEnabled(True)
    stop_btn.setEnabled(False)

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

analog_axis  = pg.PlotWidget(title="Analog signal" , labels={'left':'Volts'})
digital_axis = pg.PlotWidget(title="Digital signal", labels={'left': 'Level', 'bottom':'Time (seconds)'})
port_text_label = QtGui.QLabel("Serial port:")
port_text = QtGui.QLineEdit(port)
connect_btn = QtGui.QPushButton('Connect')
start_btn   = QtGui.QPushButton('Start')
stop_btn    = QtGui.QPushButton('Stop')
quit_btn    = QtGui.QPushButton('Quit')     

# Setup Axis.

analog_plot  = analog_axis.plot(x, signal)
digital_plot = digital_axis.plot(x, digital)
analog_axis.setYRange(0, 3.3, padding=0)
analog_axis.setXRange( -history_dur, history_dur*0.02, padding=0)
digital_axis.setYRange(-0.1, 1.1, padding=0)
digital_axis.setXRange(-history_dur, history_dur*0.02, padding=0)

## Create layout

vertical_layout   = QtGui.QVBoxLayout()
horizontal_layout = QtGui.QHBoxLayout()

horizontal_layout.addWidget(port_text_label)
horizontal_layout.addWidget(port_text)
horizontal_layout.addWidget(connect_btn)
horizontal_layout.addWidget(start_btn)
horizontal_layout.addWidget(stop_btn)
horizontal_layout.addWidget(quit_btn)
vertical_layout.addLayout(horizontal_layout)
vertical_layout.addWidget(analog_axis,  70)
vertical_layout.addWidget(digital_axis, 25)

w.setLayout(vertical_layout)

# Connect buttons

port_text.textChanged.connect(port_text_change)
connect_btn.clicked.connect(connect)
start_btn.clicked.connect(start)
stop_btn.clicked.connect(stop)
quit_btn.clicked.connect(quit)
start_btn.setEnabled(False)
stop_btn.setEnabled(False)

# Setup timer to call update().

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(10)

# Start App.

w.show() 
app.exec_()