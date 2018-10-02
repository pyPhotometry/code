# Code which runs on host computer and implements the graphical user interface.
# Copyright (c) Thomas Akam 2018.  Licenced under the GNU General Public License v3.

import os
from pyqtgraph.Qt import QtGui, QtCore
from serial import SerialException
from serial.tools import list_ports

import config
from acquisition_board import Acquisition_board
from pyboard import PyboardError
from plotting import Analog_plot, Digital_plot, Event_triggered_plot, Record_clock

class Photometry_GUI(QtGui.QWidget):

    def __init__(self, parent=None):
        super(QtGui.QWidget, self).__init__(parent)
        self.setWindowTitle('pyPhotometry GUI v{}'.format(config.VERSION))
        self.sizeHint = lambda: QtCore.QSize (900, 1080)

        # Variables

        self.board = None
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.subject_ID = ''
        self.running = False
        self.connected = False
        self.refresh_interval = 1000 # Interval to refresh tasks and ports when not running (ms).
        self.available_ports = None

        # GUI status groupbox.

        self.status_groupbox = QtGui.QGroupBox('GUI status')

        self.status_text = QtGui.QLineEdit('Not connected')
        self.status_text.setStyleSheet('background-color:rgb(210, 210, 210);')
        self.status_text.setReadOnly(True)

        self.guigroup_layout = QtGui.QHBoxLayout()
        self.guigroup_layout.addWidget(self.status_text)
        self.status_groupbox.setLayout(self.guigroup_layout)  

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
        self.mode_select.addItems(['2 colour continuous', '1 colour time div.', '2 colour time div.'])
        index = self.mode_select.findText(config.default_mode, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.mode_select.setCurrentIndex(index)
        self.rate_label = QtGui.QLabel('Sampling rate (Hz):')
        self.rate_text = QtGui.QLineEdit()
        self.rate_text.setFixedWidth(40)

        self.acquisitiongroup_layout = QtGui.QHBoxLayout()
        self.acquisitiongroup_layout.addWidget(self.mode_label)
        self.acquisitiongroup_layout.addWidget(self.mode_select)
        self.acquisitiongroup_layout.addWidget(self.rate_label)
        self.acquisitiongroup_layout.addWidget(self.rate_text)
        self.acquisition_groupbox.setLayout(self.acquisitiongroup_layout)

        self.mode_select.activated[str].connect(self.select_mode)
        self.rate_text.textChanged.connect(self.rate_text_change)

        # Current groupbox

        self.current_groupbox = QtGui.QGroupBox('LED current (mA)')

        self.current_label_1 = QtGui.QLabel('CH1:')
        self.current_spinbox_1 = QtGui.QSpinBox()
        self.current_label_2 = QtGui.QLabel('CH2:')
        self.current_spinbox_2 = QtGui.QSpinBox()  

        self.currentgroup_layout = QtGui.QHBoxLayout()
        self.currentgroup_layout.addWidget(self.current_label_1)
        self.currentgroup_layout.addWidget(self.current_spinbox_1)
        self.currentgroup_layout.addWidget(self.current_label_2)
        self.currentgroup_layout.addWidget(self.current_spinbox_2)
        self.current_groupbox.setLayout(self.currentgroup_layout)

        self.current_spinbox_1.setRange(0,100)
        self.current_spinbox_2.setRange(0,100)
        self.current_spinbox_1.setValue(config.default_LED_current[0])
        self.current_spinbox_2.setValue(config.default_LED_current[1])

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
        self.event_triggered_plot = Event_triggered_plot()

        self.record_clock = Record_clock(self.analog_plot.axis)

        # Main layout

        self.vertical_layout     = QtGui.QVBoxLayout()
        self.horizontal_layout_1 = QtGui.QHBoxLayout()
        self.horizontal_layout_2 = QtGui.QHBoxLayout()
        self.plot_splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        self.horizontal_layout_1.addWidget(self.status_groupbox)
        self.horizontal_layout_1.addWidget(self.board_groupbox)
        self.horizontal_layout_1.addWidget(self.acquisition_groupbox)
        self.horizontal_layout_1.addWidget(self.current_groupbox)
        self.horizontal_layout_2.addWidget(self.file_groupbox)
        self.horizontal_layout_2.addWidget(self.controls_groupbox)
        self.plot_splitter.addWidget(self.analog_plot.axis)
        self.plot_splitter.addWidget(self.digital_plot.axis)
        self.plot_splitter.addWidget(self.event_triggered_plot.axis)
        self.plot_splitter.setSizes([300,120,200])

        self.vertical_layout.addLayout(self.horizontal_layout_1)
        self.vertical_layout.addLayout(self.horizontal_layout_2)
        self.vertical_layout.addWidget(self.plot_splitter)

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
            self.board = Acquisition_board(self.port_select.currentText())
            self.select_mode(self.mode_select.currentText())
            self.port_select.setEnabled(False)
            self.acquisition_groupbox.setEnabled(True)
            self.current_groupbox.setEnabled(True)
            self.file_groupbox.setEnabled(True)
            self.controls_groupbox.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.connect_button.setText('Disconnect')
            self.status_text.setText('Connected')
            self.board.set_LED_current(self.current_spinbox_1.value(),self.current_spinbox_2.value())
            self.current_spinbox_1.valueChanged.connect(
                lambda v:self.board.set_LED_current(LED_1_current=int(v)))
            self.current_spinbox_2.valueChanged.connect(
                lambda v:self.board.set_LED_current(LED_2_current=int(v)))
            self
            self.connected = True
        except SerialException:
            self.status_text.setText('Connection failed')
        except PyboardError:
            self.status_text.setText('Firmware error')
            self.board.close()

    def disconnect(self):
        # Disconnect from pyboard.
        if self.board: self.board.close()
        self.board = None
        self.acquisition_groupbox.setEnabled(False)
        self.current_groupbox.setEnabled(False)
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
        self.event_triggered_plot.reset(self.board.sampling_rate)
        # Start acquisition.
        self.board.start()
        self.refresh_timer.stop()
        self.update_timer.start(config.update_interval)
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
            self.current_groupbox.setEnabled(False)
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
        self.current_groupbox.setEnabled(True)
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
