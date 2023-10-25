import os
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from serial import SerialException

import config.GUI_config as GUI_config
from GUI.acquisition_board import Acquisition_board
from GUI.pyboard import PyboardError
from GUI.plotting import Analog_plot, Digital_plot, Event_triggered_plot, Record_clock
from GUI.utility import set_cbox_item


class Single_tab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.GUI_main = self.parent()

        # Variables

        self.board = None
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        self.subject_ID = ""
        self.running = False
        self.connected = False
        self.clipboard = QtWidgets.QApplication.clipboard()  # Used to copy strings to computer clipboard.

        # GUI status groupbox.

        self.status_groupbox = QtWidgets.QGroupBox("Status")

        self.status_text = QtWidgets.QLineEdit("Not connected")
        self.status_text.setStyleSheet("background-color:rgb(210, 210, 210);")
        self.status_text.setReadOnly(True)
        self.status_text.setFixedWidth(105)

        self.guigroup_layout = QtWidgets.QHBoxLayout()
        self.guigroup_layout.addWidget(self.status_text)
        self.status_groupbox.setLayout(self.guigroup_layout)

        # Board groupbox

        self.board_groupbox = QtWidgets.QGroupBox("Board")

        self.port_label = QtWidgets.QLabel("Serial port:")
        self.port_select = QtWidgets.QComboBox()
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.connect_button.setFixedWidth(110)

        self.boardgroup_layout = QtWidgets.QHBoxLayout()
        self.boardgroup_layout.addWidget(self.port_label)
        self.boardgroup_layout.addWidget(self.port_select)
        self.boardgroup_layout.addWidget(self.connect_button)
        self.board_groupbox.setLayout(self.boardgroup_layout)

        self.connect_button.clicked.connect(lambda: self.disconnect() if self.connected else self.connect())

        # Settings groupbox

        self.settings_groupbox = QtWidgets.QGroupBox("Acquisition settings")

        self.mode_label = QtWidgets.QLabel("Mode:")
        self.mode_select = QtWidgets.QComboBox()
        self.mode_select.addItems(["2 colour continuous", "1 colour time div.", "2 colour time div."])
        set_cbox_item(self.mode_select, GUI_config.default_acquisition_mode)
        self.rate_label = QtWidgets.QLabel("Sampling rate (Hz):")
        self.rate_text = QtWidgets.QLineEdit()
        self.rate_text.setFixedWidth(40)

        self.settingsgroup_layout = QtWidgets.QHBoxLayout()
        self.settingsgroup_layout.addWidget(self.mode_label)
        self.settingsgroup_layout.addWidget(self.mode_select)
        self.settingsgroup_layout.addWidget(self.rate_label)
        self.settingsgroup_layout.addWidget(self.rate_text)
        self.settings_groupbox.setLayout(self.settingsgroup_layout)

        self.mode_select.textActivated[str].connect(self.select_mode)
        self.rate_text.textChanged.connect(self.rate_text_change)

        # Current groupbox

        self.current_groupbox = QtWidgets.QGroupBox("LED current (mA)")

        self.current_label_1 = QtWidgets.QLabel("CH1:")
        self.current_spinbox_1 = QtWidgets.QSpinBox()
        self.current_spinbox_1.setFixedWidth(50)

        self.current_label_2 = QtWidgets.QLabel("CH2:")
        self.current_spinbox_2 = QtWidgets.QSpinBox()
        self.current_spinbox_2.setFixedWidth(50)

        self.currentgroup_layout = QtWidgets.QHBoxLayout()
        self.currentgroup_layout.addWidget(self.current_label_1)
        self.currentgroup_layout.addWidget(self.current_spinbox_1)
        self.currentgroup_layout.addWidget(self.current_label_2)
        self.currentgroup_layout.addWidget(self.current_spinbox_2)
        self.current_groupbox.setLayout(self.currentgroup_layout)

        self.current_spinbox_1.setValue(GUI_config.default_LED_current[0])
        self.current_spinbox_2.setValue(GUI_config.default_LED_current[1])

        # File groupbox

        self.file_groupbox = QtWidgets.QGroupBox("Data file")

        self.data_dir_label = QtWidgets.QLabel("Data dir:")
        self.data_dir_text = QtWidgets.QLineEdit(self.data_dir)
        self.data_dir_button = QtWidgets.QPushButton("")
        self.data_dir_button.setIcon(QtGui.QIcon("GUI/icons/folder.svg"))
        self.data_dir_button.setFixedWidth(30)
        self.subject_label = QtWidgets.QLabel("Subject ID:")
        self.subject_text = QtWidgets.QLineEdit(self.subject_ID)
        self.subject_text.setFixedWidth(80)
        self.subject_text.setMaxLength(12)
        self.filetype_label = QtWidgets.QLabel("File type:")
        self.filetype_select = QtWidgets.QComboBox()
        self.filetype_select.addItems(["ppd", "csv"])
        set_cbox_item(self.filetype_select, GUI_config.default_filetype)

        self.filegroup_layout = QtWidgets.QHBoxLayout()
        self.filegroup_layout.addWidget(self.data_dir_label)
        self.filegroup_layout.addWidget(self.data_dir_text)
        self.filegroup_layout.addWidget(self.data_dir_button)
        self.filegroup_layout.addWidget(self.subject_label)
        self.filegroup_layout.addWidget(self.subject_text)
        self.filegroup_layout.addWidget(self.filetype_label)
        self.filegroup_layout.addWidget(self.filetype_select)
        self.file_groupbox.setLayout(self.filegroup_layout)

        self.data_dir_text.textChanged.connect(self.test_data_path)
        self.data_dir_button.clicked.connect(self.select_data_dir)
        self.subject_text.textChanged.connect(self.test_data_path)

        # Acquisition groupbox

        self.acquisition_groupbox = QtWidgets.QGroupBox("Acquisition")

        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setIcon(QtGui.QIcon("GUI/icons/play.svg"))
        self.record_button = QtWidgets.QPushButton("Record")
        self.record_button.setIcon(QtGui.QIcon("GUI/icons/record.svg"))
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setIcon(QtGui.QIcon("GUI/icons/stop.svg"))

        self.acquisitiongroup_layout = QtWidgets.QHBoxLayout()
        self.acquisitiongroup_layout.addWidget(self.start_button)
        self.acquisitiongroup_layout.addWidget(self.record_button)
        self.acquisitiongroup_layout.addWidget(self.stop_button)
        self.acquisition_groupbox.setLayout(self.acquisitiongroup_layout)

        self.start_button.clicked.connect(self.start)
        self.record_button.clicked.connect(self.record)
        self.stop_button.clicked.connect(self.stop)

        # Plots

        self.analog_plot = Analog_plot(self)
        self.digital_plot = Digital_plot()
        self.event_triggered_plot = Event_triggered_plot()

        self.record_clock = Record_clock(self.analog_plot.axis)

        # Main layout

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.horizontal_layout_1 = QtWidgets.QHBoxLayout()
        self.horizontal_layout_2 = QtWidgets.QHBoxLayout()
        self.plot_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        self.horizontal_layout_1.addWidget(self.status_groupbox)
        self.horizontal_layout_1.addWidget(self.board_groupbox)
        self.horizontal_layout_1.addWidget(self.settings_groupbox)
        self.horizontal_layout_1.addWidget(self.current_groupbox)
        self.horizontal_layout_2.addWidget(self.file_groupbox)
        self.horizontal_layout_2.addWidget(self.acquisition_groupbox)
        self.plot_splitter.addWidget(self.analog_plot)
        self.plot_splitter.addWidget(self.digital_plot.axis)
        self.plot_splitter.addWidget(self.event_triggered_plot.axis)
        self.plot_splitter.setSizes([300, 120, 200])

        self.vertical_layout.addLayout(self.horizontal_layout_1)
        self.vertical_layout.addLayout(self.horizontal_layout_2)
        self.vertical_layout.addWidget(self.plot_splitter)

        self.setLayout(self.vertical_layout)

        # Setup Timers.

        self.update_timer = QtCore.QTimer()  # Timer to regularly call process_data()
        self.update_timer.timeout.connect(self.process_data)

        # Initial setup.

        self.disconnect()  # Set initial state as disconnected.

    # Button and box functions -------------------------------------------

    def connect(self):
        try:
            self.status_text.setText("Connecting")
            self.connect_button.setEnabled(False)
            self.GUI_main.app.processEvents()
            self.board = Acquisition_board(self.port_select.currentText())
            self.select_mode(self.mode_select.currentText())
            self.port_select.setEnabled(False)
            self.settings_groupbox.setEnabled(True)
            self.current_groupbox.setEnabled(True)
            self.file_groupbox.setEnabled(True)
            self.acquisition_groupbox.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.connect_button.setText("Disconnect")
            self.connect_button.setIcon(QtGui.QIcon("GUI/icons/disconnect.svg"))
            self.status_text.setText("Connected")
            self.connect_button.setEnabled(True)
            self.board.set_LED_current(self.current_spinbox_1.value(), self.current_spinbox_2.value())
            self.current_spinbox_1.valueChanged.connect(lambda v: self.board.set_LED_current(LED_1_current=int(v)))
            self.current_spinbox_2.valueChanged.connect(lambda v: self.board.set_LED_current(LED_2_current=int(v)))
            self
            self.connected = True
        except SerialException:
            self.status_text.setText("Connection failed")
            self.connect_button.setEnabled(True)
            raise
        except PyboardError:
            self.status_text.setText("Connection failed")
            self.connect_button.setEnabled(True)
            raise
            try:
                self.board.close()
            except AttributeError:
                pass

    def disconnect(self):
        """Disconnect from pyboard."""
        if self.running:
            self.stop()
        if self.board:
            self.board.close()
        self.board = None
        self.settings_groupbox.setEnabled(False)
        self.current_groupbox.setEnabled(False)
        self.file_groupbox.setEnabled(False)
        self.acquisition_groupbox.setEnabled(False)
        self.port_select.setEnabled(True)
        self.connect_button.setText("Connect")
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.status_text.setText("Not connected")
        self.connected = False

    def test_data_path(self):
        """Checks whether data dir and subject ID are valid."""
        self.data_dir = self.data_dir_text.text()
        self.subject_ID = self.subject_text.text()
        if self.running and os.path.isdir(self.data_dir) and str(self.subject_ID):
            self.record_button.setEnabled(True)

    def select_mode(self, mode):
        self.board.set_mode(mode)
        self.rate_text.setText(str(self.board.sampling_rate))
        self.current_spinbox_1.setRange(0, self.board.max_LED_current)
        self.current_spinbox_2.setRange(0, self.board.max_LED_current)
        if self.current_spinbox_1.value() > self.board.max_LED_current:
            self.current_spinbox_1.setValue(self.board.max_LED_current)
            self.board.set_LED_current(LED_1_current=self.board.max_LED_current)
        if self.current_spinbox_2.value() > self.board.max_LED_current:
            self.current_spinbox_2.setValue(self.board.max_LED_current)
            self.board.set_LED_current(LED_2_current=self.board.max_LED_current)

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
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select data folder", self.data_dir)
        )

    def start(self):
        # Reset plots.
        self.analog_plot.reset(self.board.sampling_rate)
        self.digital_plot.reset(self.board.sampling_rate)
        self.event_triggered_plot.reset(self.board.sampling_rate)
        # Start acquisition.
        self.board.start()
        self.GUI_main.refresh_timer.stop()
        self.update_timer.start(GUI_config.update_interval)
        self.running = True
        # Update UI.
        self.board_groupbox.setEnabled(False)
        self.settings_groupbox.setEnabled(False)
        self.start_button.setEnabled(False)
        if self.test_data_path():
            self.record_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_text.setText("Running")

    def record(self):
        if os.path.isdir(self.data_dir):
            filetype = self.filetype_select.currentText()
            file_name = self.board.record(self.data_dir, self.subject_ID, filetype)
            self.clipboard.setText(file_name)
            self.status_text.setText("Recording")
            self.current_groupbox.setEnabled(False)
            self.file_groupbox.setEnabled(False)
            self.record_button.setEnabled(False)
            self.subject_text.setEnabled(False)
            self.data_dir_text.setEnabled(False)
            self.data_dir_button.setEnabled(False)
            self.record_clock.start()
        else:
            self.data_dir_text.setText("Set valid directory")
            self.data_dir_label.setStyleSheet("color: rgb(255, 0, 0);")

    def stop(self, error=False):
        self.board.stop()
        self.update_timer.stop()
        self.GUI_main.refresh_timer.start(self.GUI_main.refresh_interval)
        self.running = False
        self.stop_button.setEnabled(False)
        self.board.serial.reset_input_buffer()
        self.board_groupbox.setEnabled(True)
        self.settings_groupbox.setEnabled(True)
        self.current_groupbox.setEnabled(True)
        self.file_groupbox.setEnabled(True)
        self.start_button.setEnabled(True)
        self.record_button.setEnabled(False)
        self.subject_text.setEnabled(True)
        self.data_dir_text.setEnabled(True)
        self.data_dir_button.setEnabled(True)
        if error:
            self.status_text.setText("Error")
        else:
            self.status_text.setText("Connected")
        self.record_clock.stop()

    def serial_connection_lost(self):
        if self.running:
            self.update_timer.stop()
            self.GUI_main.refresh_timer.start(self.refresh_interval)
            self.running = False
            self.board_groupbox.setEnabled(True)
            self.start_button.setEnabled(True)
            self.board.stop_recording()
            self.record_clock.stop()
        self.disconnect()
        QtWidgets.QMessageBox.question(
            self, "Error", "Serial connection lost.", QtWidgets.QMessageBox.StandardButton.Ok
        )

    # Timer callbacks.

    def process_data(self):
        """Called regularly while running, read data from the serial port and update the plot."""
        try:
            data = self.board.process_data()
        except PyboardError:
            self.stop(error=True)
            raise
        if data:
            new_ADC1, new_ADC2, new_DI1, new_DI2 = data
            # Update plots.
            self.analog_plot.update(new_ADC1, new_ADC2, new_DI1, new_DI2)
            self.digital_plot.update(new_DI1, new_DI2)
            self.event_triggered_plot.update(new_DI1, self.digital_plot, self.analog_plot)
            self.record_clock.update()

    def refresh(self):
        """Called regularly while not running, scan serial ports for connected boards and update ports list if changed."""
        if self.GUI_main.ports_changed:
            self.port_select.clear()
            self.port_select.addItems(sorted(self.GUI_main.available_ports))