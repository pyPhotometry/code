# Code which runs on host computer and implements the graphical user interface.

import os
from pyqtgraph.Qt import QtGui, QtCore
from serial import SerialException
from serial.tools import list_ports

from photometry_host import Photometry_host
from config import pins, update_interval
from plotting import Analog_plot, Digital_plot, Correlation_plot, Event_triggered_plot

# Variables ---------------------------------------------------------
board = None
port  = 'com1'
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
subject_ID = 's001'
running = False

# Update -----------------------------------------------------------

def update():
    # Read data from the serial port and update the plot.
    if board:
        data = board.process_data()
        if data:
            new_ADC1, new_ADC2, new_DI1, new_DI2 = data
            # Update plots.
            analog.update(new_ADC1, new_ADC2)
            digital.update(new_DI1, new_DI2)
            correlation.update(analog)
            event_triggered.update(new_DI1, digital, analog)

# Button and box functions -------------------------------------------

def select_mode(mode):
    board.set_mode(mode)
    rate_text.setText(str(board.sampling_rate))

def data_dir_text_change(text):
    global data_dir
    data_dir = text
    data_dir_label.setStyleSheet('')

def subject_text_change(text):
    global subject_ID
    subject_ID = text

def rate_text_change(text):
    if text:
        try:
            sampling_rate = int(text)
        except ValueError:
            rate_text.setText(str(board.sampling_rate))
            return
        set_rate = board.set_sampling_rate(sampling_rate)
        rate_text.setText(str(set_rate))

def connect():
    global board
    try:
        board = Photometry_host(port_select.currentText(), pins)
        select_mode(mode_select.currentText())
        start_button.setEnabled(True)
        connect_button.setEnabled(False)
        port_select.setEnabled(False)
        rate_text.setEnabled(True)
        status_text.setText('Connected')
    except SerialException:
        status_text.setText('Connection failed')

def select_data_dir():
    global data_dir
    data_dir = QtGui.QFileDialog.getExistingDirectory(w, 'Select data folder')
    data_dir_text.setText(data_dir)
    data_dir_label.setStyleSheet("color: rgb(0, 0, 0);")

def start():
    global running
    # Reset plots.
    analog.reset(board.sampling_rate)
    digital.reset(board.sampling_rate)
    correlation.reset(board.sampling_rate)
    event_triggered.reset(board.sampling_rate)
    # Start acquisition.
    update_timer.start(update_interval)
    board.start()
    running = True
    # Update UI.
    mode_select.setEnabled(False)
    start_button.setEnabled(False)
    record_button.setEnabled(True)
    stop_button.setEnabled(True)
    rate_text.setEnabled(False)
    status_text.setText('Running')

def record():
    global data_dir, subject_ID, board
    if os.path.isdir(data_dir):
        board.record(data_dir, subject_ID)
        status_text.setText('Recording')
        analog.recording.setText('Recording')
        record_button.setEnabled(False)
        subject_text.setEnabled(False)
        data_dir_text.setEnabled(False)
        data_dir_button.setEnabled(False)
    else:
        data_dir_text.setText('Set valid directory')
        data_dir_label.setStyleSheet("color: rgb(255, 0, 0);")

def stop():
    global board, running
    update_timer.stop()
    board.stop()
    running = False
    mode_select.setEnabled(True)
    stop_button.setEnabled(False)
    subject_text.setEnabled(True)
    data_dir_text.setEnabled(True)
    data_dir_button.setEnabled(True)
    rate_text.setEnabled(True)
    start_available_timer.start(500)
    status_text.setText('Connected')
    analog.recording.setText('')

def start_available():
    start_button.setEnabled(True)

def quit_func():
    global board, running
    if running: stop()
    if board: board.close()

# Main  -----------------------------------------------------------

app = QtGui.QApplication([])  # Start QT
app.aboutToQuit.connect(quit_func)

## Create widgets.

w = QtGui.QWidget()
w.setWindowTitle('pyPhotometry GUI')

status_label = QtGui.QLabel("Status:")
status_text = QtGui.QLineEdit('Not connected')
status_text.setStyleSheet('background-color:rgb(210, 210, 210);')
status_text.setReadOnly(True)
mode_label = QtGui.QLabel("Mode:")
mode_select = QtGui.QComboBox()
mode_select.addItem('GCaMP/RFP')
mode_select.addItem('GCaMP/iso')
port_label = QtGui.QLabel("Serial port:")

ports = set([c[0] for c in list_ports.comports()
             if ('Pyboard' in c[1]) or ('USB Serial Device' in c[1])])
port_select = QtGui.QComboBox()
port_select.addItems(ports)

rate_label = QtGui.QLabel('Sampling rate (Hz):')
rate_text = QtGui.QLineEdit()
rate_text.setFixedWidth(50)
data_dir_label = QtGui.QLabel("Data dir:")
data_dir_text = QtGui.QLineEdit(data_dir)
data_dir_button = QtGui.QPushButton('...')
data_dir_button.setFixedWidth(30)
subject_label = QtGui.QLabel("Subject ID:")
subject_text = QtGui.QLineEdit(subject_ID)
subject_text.setFixedWidth(80)
subject_text.setMaxLength(12)
connect_button = QtGui.QPushButton('Connect')
start_button = QtGui.QPushButton('Start')
record_button= QtGui.QPushButton('Record')
stop_button = QtGui.QPushButton('Stop')

# Instantiate plotter classes.
analog  = Analog_plot()
digital = Digital_plot()
correlation = Correlation_plot()
event_triggered = Event_triggered_plot()

## Create layout

vertical_layout     = QtGui.QVBoxLayout()
horizontal_layout_1 = QtGui.QHBoxLayout()
horizontal_layout_2 = QtGui.QHBoxLayout()
horizontal_layout_3 = QtGui.QHBoxLayout()

horizontal_layout_1.addWidget(status_label)
horizontal_layout_1.addWidget(status_text)
horizontal_layout_1.addWidget(port_label)
horizontal_layout_1.addWidget(port_select)
horizontal_layout_1.addWidget(connect_button)
horizontal_layout_1.addWidget(mode_label)
horizontal_layout_1.addWidget(mode_select)
horizontal_layout_1.addWidget(rate_label)
horizontal_layout_1.addWidget(rate_text)
horizontal_layout_2.addWidget(data_dir_label)
horizontal_layout_2.addWidget(data_dir_text)
horizontal_layout_2.addWidget(data_dir_button)
horizontal_layout_2.addWidget(subject_label)
horizontal_layout_2.addWidget(subject_text)
horizontal_layout_2.addWidget(start_button)
horizontal_layout_2.addWidget(record_button)
horizontal_layout_2.addWidget(stop_button)

horizontal_layout_3.addWidget(correlation.axis, 40)
horizontal_layout_3.addWidget(event_triggered.axis, 60)

vertical_layout.addLayout(horizontal_layout_1)
vertical_layout.addLayout(horizontal_layout_2)
vertical_layout.addWidget(analog.axis,  40)
vertical_layout.addWidget(digital.axis, 15)
vertical_layout.addLayout(horizontal_layout_3, 40)

w.setLayout(vertical_layout)

# Connect buttons, boxes etc.

mode_select.activated[str].connect(select_mode)
rate_text.textChanged.connect(rate_text_change)
data_dir_text.textChanged.connect(data_dir_text_change)
subject_text.textChanged.connect(subject_text_change)
connect_button.clicked.connect(connect)
data_dir_button.clicked.connect(select_data_dir)
start_button.clicked.connect(start)
record_button.clicked.connect(record)
stop_button.clicked.connect(stop)
rate_text.setEnabled(False)
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