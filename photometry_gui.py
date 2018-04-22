# Code which runs on host computer and implements the graphical user interface.

import os
from pyqtgraph.Qt import QtGui, QtCore
from serial import SerialException
from serial.tools import list_ports

from photometry_host import Photometry_host
from config import pins, update_interval
from plotting import Analog_plot, Digital_plot, Correlation_plot, Event_triggered_plot, Record_clock

class Photometry_GUI(QtGui.QWidget):

    def __init__(self, parent=None):
        super(QtGui.QWidget, self).__init__(parent)
        self.setWindowTitle('pyPhotometry GUI')
        self.sizeHint = lambda: QtCore.QSize (600, 1080)

        # Variables

        self.board = None
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.subject_ID = ''
        self.running = False
        self.connected = False
        self.refresh_interval = 1000 # Interval to refresh tasks and ports when not running (ms).
        self.available_ports = None

        # GUI groupbox.

        self.gui_groupbox = QtGui.QGroupBox('GUI')

        self.status_label = QtGui.QLabel('Status:')
        self.status_text = QtGui.QLineEdit('Not connected')
        self.status_text.setStyleSheet('background-color:rgb(210, 210, 210);')
        self.status_text.setReadOnly(True)

        self.guigroup_layout = QtGui.QHBoxLayout()
        self.guigroup_layout.addWidget(self.status_label)
        self.guigroup_layout.addWidget(self.status_text)
        self.gui_groupbox.setLayout(self.guigroup_layout)  

        # Board groupbox

        self.board_groupbox = QtGui.QGroupBox('Board')

        self.port_label = QtGui.QLabel("Serial port:")
        self.port_select = QtGui.QComboBox()
        self.connect_button = QtGui.QPushButton('Connect')

        self.boardgroup_layout = QtGui.QHBoxLayout()
        self.boardgroup_layout.addWidget(self.port_label)
        self.boardgroup_layout.addWidget(self.port_select)
        self.boardgroup_layout.addWidget(self.connect_button)
        self.board_groupbox.setLayout(self.boardgroup_layout)

        self.connect_button.clicked.connect(
            lambda: self.disconnect() if self.connected else self.connect())

        # Acquisition groupbox

        self.acquisition_groupbox = QtGui.QGroupBox('Acquisition settings')        

        self.mode_label = QtGui.QLabel("Mode:")
        self.mode_select = QtGui.QComboBox()
        self.mode_select.addItems(['GCaMP/RFP', 'GCaMP/iso', 'GCaMP/RFP_dif'])
        self.rate_label = QtGui.QLabel('Sampling rate (Hz):')
        self.rate_text = QtGui.QLineEdit()

        self.acquisitiongroup_layout = QtGui.QHBoxLayout()
        self.acquisitiongroup_layout.addWidget(self.mode_label)
        self.acquisitiongroup_layout.addWidget(self.mode_select)
        self.acquisitiongroup_layout.addWidget(self.rate_label)
        self.acquisitiongroup_layout.addWidget(self.rate_text)
        self.acquisition_groupbox.setLayout(self.acquisitiongroup_layout)

        self.mode_select.activated[str].connect(self.select_mode)
        self.rate_text.textChanged.connect(self.rate_text_change)

        # File groupbox

        self.file_groupbox = QtGui.QGroupBox('Data file')

        self.data_dir_label = QtGui.QLabel("Data dir:")
        self.data_dir_text = QtGui.QLineEdit(self.data_dir)
        self.data_dir_button = QtGui.QPushButton('...')
        self.data_dir_button.setFixedWidth(30)
        self.subject_label = QtGui.QLabel("Subject ID:")
        self.subject_text = QtGui.QLineEdit(self.subject_ID)
        self.subject_text.setFixedWidth(80)
        self.subject_text.setMaxLength(12)

        self.filegroup_layout = QtGui.QHBoxLayout()
        self.filegroup_layout.addWidget(self.data_dir_label)
        self.filegroup_layout.addWidget(self.data_dir_text)
        self.filegroup_layout.addWidget(self.data_dir_button)
        self.filegroup_layout.addWidget(self.subject_label)
        self.filegroup_layout.addWidget(self.subject_text)
        self.file_groupbox.setLayout(self.filegroup_layout)

        self.data_dir_text.textChanged.connect(self.test_data_path)
        self.data_dir_button.clicked.connect(self.select_data_dir)
        self.subject_text.textChanged.connect(self.test_data_path)

        # Controls groupbox

        self.controls_groupbox = QtGui.QGroupBox('Controls')

        self.start_button = QtGui.QPushButton('Start')
        self.record_button = QtGui.QPushButton('Record')
        self.stop_button = QtGui.QPushButton('Stop')

        self.controlsgroup_layout = QtGui.QHBoxLayout()
        self.controlsgroup_layout.addWidget(self.start_button)
        self.controlsgroup_layout.addWidget(self.record_button)
        self.controlsgroup_layout.addWidget(self.stop_button)
        self.controls_groupbox.setLayout(self.controlsgroup_layout)

        self.start_button.clicked.connect(self.start)
        self.record_button.clicked.connect(self.record)
        self.stop_button.clicked.connect(self.stop)

        # Plots

        self.analog_plot  = Analog_plot()
        self.digital_plot = Digital_plot()
        self.correlation_plot = Correlation_plot()
        self.event_triggered_plot = Event_triggered_plot()

        self.record_clock = Record_clock(self.analog_plot.axis)

        # Main layout

        self.vertical_layout     = QtGui.QVBoxLayout()
        self.horizontal_layout_1 = QtGui.QHBoxLayout()
        self.horizontal_layout_2 = QtGui.QHBoxLayout()
        self.horizontal_layout_3 = QtGui.QHBoxLayout()

        self.horizontal_layout_1.addWidget(self.gui_groupbox)
        self.horizontal_layout_1.addWidget(self.board_groupbox)
        self.horizontal_layout_1.addWidget(self.acquisition_groupbox)
        self.horizontal_layout_2.addWidget(self.file_groupbox)
        self.horizontal_layout_2.addWidget(self.controls_groupbox)
        self.horizontal_layout_3.addWidget(self.correlation_plot.axis, 30)
        self.horizontal_layout_3.addWidget(self.event_triggered_plot.axis, 60)

        self.vertical_layout.addLayout(self.horizontal_layout_1)
        self.vertical_layout.addLayout(self.horizontal_layout_2)
        self.vertical_layout.addWidget(self.analog_plot.axis,  40)
        self.vertical_layout.addWidget(self.digital_plot.axis, 15)
        self.vertical_layout.addLayout(self.horizontal_layout_3, 40)

        self.setLayout(self.vertical_layout)

        # Setup Timers.

        self.update_timer = QtCore.QTimer() # Timer to regularly call process_data()
        self.update_timer.timeout.connect(self.process_data)
        self.refresh_timer = QtCore.QTimer() # Timer to regularly call refresh() when not running.
        self.refresh_timer.timeout.connect(self.refresh)

        # Initial setup.

        self.disconnect() # Set initial state as disconnected.
        self.refresh()    # Refresh ports list.
        self.refresh_timer.start(self.refresh_interval) 

    # Button and box functions -------------------------------------------

    def connect(self):
        try:
            self.board = Photometry_host(self.port_select.currentText(), pins)
            self.select_mode(self.mode_select.currentText())
            self.port_select.setEnabled(False)
            self.acquisition_groupbox.setEnabled(True)
            self.file_groupbox.setEnabled(True)
            self.controls_groupbox.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.connect_button.setText('Disconnect')
            self.status_text.setText('Connected')
            self.connected = True
        except SerialException:
            self.status_text.setText('Connection failed')

    def disconnect(self):
        # Disconnect from pyboard.
        if self.board: self.board.close()
        self.board = None
        self.acquisition_groupbox.setEnabled(False)
        self.file_groupbox.setEnabled(False)
        self.controls_groupbox.setEnabled(False)
        self.port_select.setEnabled(True)
        self.connect_button.setText('Connect')
        self.status_text.setText('Not connected')
        self.connected = False

    def test_data_path(self):
        # Checks whether data dir and subject ID are valid.
        self.data_dir = self.data_dir_text.text()
        self.subject_ID = self.subject_text.text()
        if (self.running and os.path.isdir(self.data_dir) and str(self.subject_ID)):
                self.record_button.setEnabled(True)      

    def select_mode(self, mode):
        self.board.set_mode(mode)
        self.rate_text.setText(str(self.board.sampling_rate))

    def rate_text_change(self, text):
        if text:
            try:
                sampling_rate = int(text)
            except ValueError:
                self.rate_text.setText(str(self.board.sampling_rate))
                return
            set_rate = self.board.set_sampling_rate(sampling_rate)
            self.rate_text.setText(str(set_rate))

    def select_data_dir(self):
        self.data_dir_text.setText(
            QtGui.QFileDialog.getExistingDirectory(self, 'Select data folder', self.data_dir))

    def start(self):
        # Reset plots.
        self.analog_plot.reset(self.board.sampling_rate)
        self.digital_plot.reset(self.board.sampling_rate)
        self.correlation_plot.reset(self.board.sampling_rate)
        self.event_triggered_plot.reset(self.board.sampling_rate)
        # Start acquisition.
        self.board.start()
        self.refresh_timer.stop()
        self.update_timer.start(update_interval)
        self.running = True
        # Update UI.
        self.board_groupbox.setEnabled(False)
        self.acquisition_groupbox.setEnabled(False)
        self.start_button.setEnabled(False)
        if self.test_data_path():
            self.record_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_text.setText('Running')

    def record(self):
        if os.path.isdir(self.data_dir):
            self.board.record(self.data_dir, self.subject_ID)
            self.status_text.setText('Recording')
            self.record_button.setEnabled(False)
            self.subject_text.setEnabled(False)
            self.data_dir_text.setEnabled(False)
            self.data_dir_button.setEnabled(False)
            self.record_clock.start()
        else:
            self.data_dir_text.setText('Set valid directory')
            self.data_dir_label.setStyleSheet("color: rgb(255, 0, 0);")

    def stop(self):
        self.board.stop()
        self.update_timer.stop()
        self.refresh_timer.start(self.refresh_interval)
        self.running = False
        self.stop_button.setEnabled(False)
        self.board.serial.reset_input_buffer()
        self.board_groupbox.setEnabled(True)
        self.acquisition_groupbox.setEnabled(True)
        self.start_button.setEnabled(True)
        self.record_button.setEnabled(False)
        self.subject_text.setEnabled(True)
        self.data_dir_text.setEnabled(True)
        self.data_dir_button.setEnabled(True)
        self.status_text.setText('Connected')
        self.record_clock.stop()

    # Timer callbacks.

    def process_data(self):
        # Called regularly while running, read data from the serial port
        # and update the plot.
        if self.board:
            data = self.board.process_data()
            if data:
                new_ADC1, new_ADC2, new_DI1, new_DI2 = data
                # Update plots.
                self.analog_plot.update(new_ADC1, new_ADC2)
                self.digital_plot.update(new_DI1, new_DI2)
                self.correlation_plot.update(self.analog_plot)
                self.event_triggered_plot.update(new_DI1, self.digital_plot, self.analog_plot)
                self.record_clock.update()

    def refresh(self):
        # Called regularly while not running, scan serial ports for 
        # connected boards and update ports list if changed.
        ports = set([c[0] for c in list_ports.comports()
                     if ('Pyboard' in c[1]) or ('USB Serial Device' in c[1])])
        if not ports == self.available_ports:
            self.port_select.clear()
            self.port_select.addItems(sorted(ports))
            self.available_ports = ports


    # Cleanup.

    def closeEvent(self, event):
        # Called when GUI window is closed.
        if self.running: self.stop()
        if self.board: self.board.close()
        event.accept()

# Main ----------------------------------------------------------------

if __name__ == '__main__':
    app = QtGui.QApplication([])  # Start QT
    photometry_GUI = Photometry_GUI()
    photometry_GUI.show()
    app.exec_()
