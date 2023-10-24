import os
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from serial import SerialException

import config.GUI_config as GUI_config
from GUI.acquisition_board import Acquisition_board
from GUI.pyboard import PyboardError
from GUI.plotting import Analog_plot, Record_clock
from GUI.utility import set_cbox_item

# ----------------------------------------------------------------------------------------
#  Multi-tab
# ----------------------------------------------------------------------------------------


class Multi_tab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.GUI_main = self.parent()

        # Variables.
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

        # Settings groupbox.

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

        # Data directory groupbox

        self.datadir_groupbox = QtWidgets.QGroupBox("Data directory")

        self.data_dir_label = QtWidgets.QLabel("Data dir:")
        self.data_dir_text = QtWidgets.QLineEdit(self.data_dir)
        self.data_dir_button = QtWidgets.QPushButton("")
        self.data_dir_button.setIcon(QtGui.QIcon("GUI/icons/folder.svg"))
        self.data_dir_button.setFixedWidth(30)
        self.filetype_label = QtWidgets.QLabel("File type:")
        self.filetype_select = QtWidgets.QComboBox()
        self.filetype_select.addItems(["ppd", "csv"])
        set_cbox_item(self.filetype_select, GUI_config.default_filetype)

        self.filegroup_layout = QtWidgets.QHBoxLayout()
        self.filegroup_layout.addWidget(self.data_dir_label)
        self.filegroup_layout.addWidget(self.data_dir_text)
        self.filegroup_layout.addWidget(self.data_dir_button)
        self.filegroup_layout.addWidget(self.filetype_label)
        self.filegroup_layout.addWidget(self.filetype_select)
        self.datadir_groupbox.setLayout(self.filegroup_layout)

        self.data_dir_text.textChanged.connect(self.test_data_path)
        self.data_dir_button.clicked.connect(self.select_data_dir)

        # Setups groupbox

        self.setups_groupbox = QtWidgets.QGroupBox("Setups")
        self.add_setup_button = QtWidgets.QPushButton("Add")
        self.add_setup_button.clicked.connect(self.add_setup)
        self.remove_setup_button = QtWidgets.QPushButton("remove")
        self.remove_setup_button.clicked.connect(self.remove_setup)

        self.setupsgroup_layout = QtWidgets.QHBoxLayout()
        self.setupsgroup_layout.addWidget(self.add_setup_button)
        self.setupsgroup_layout.addWidget(self.remove_setup_button)
        self.setups_groupbox.setLayout(self.setupsgroup_layout)

        # Config groupbox

        self.config_groupbox = QtWidgets.QGroupBox("Config")
        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.setIcon(QtGui.QIcon("GUI/icons/save.svg"))
        self.load_button = QtWidgets.QPushButton("Load")

        self.configgroup_layout = QtWidgets.QHBoxLayout()
        self.configgroup_layout.addWidget(self.save_button)
        self.configgroup_layout.addWidget(self.load_button)
        self.config_groupbox.setLayout(self.configgroup_layout)

        # Layout

        self.scroll_area = QtWidgets.QScrollArea(parent=self)
        self.scroll_area.horizontalScrollBar().setEnabled(False)
        self.scroll_inner = QtWidgets.QFrame(self)
        self.boxes_layout = QtWidgets.QVBoxLayout(self.scroll_inner)
        self.scroll_area.setWidget(self.scroll_inner)
        self.scroll_area.setWidgetResizable(True)

        self.grid_layout = QtWidgets.QGridLayout(self)
        self.grid_layout.addWidget(self.config_groupbox, 1, 1)
        self.grid_layout.addWidget(self.setups_groupbox, 1, 2)
        self.grid_layout.addWidget(self.settings_groupbox, 1, 3)
        self.grid_layout.addWidget(self.datadir_groupbox, 1, 4)
        self.grid_layout.addWidget(self.scroll_area, 2, 1, 1, 4)

        # Setupboxes

        self.setupboxes = []
        self.add_setup()
        self.add_setup()

        # Timers.

        self.update_timer = QtCore.QTimer()  # Timer to regularly call process_data()
        self.update_timer.timeout.connect(self.process_data)

        # Initial state
        self.config_groupbox.setEnabled(False)

    def add_setup(self):
        self.setupboxes.append(Setupbox(self, ID=len(self.setupboxes)))
        self.boxes_layout.addWidget(self.setupboxes[-1])

    def remove_setup(self):
        box = self.setupboxes.pop(-1)
        box.setParent(None)
        box.deleteLater()

    def setup_started(self):
        self.settings_groupbox.setEnabled(False)
        self.setups_groupbox.setEnabled(False)
        self.datadir_groupbox.setEnabled(False)
        if not self.update_timer.isActive():
            self.update_timer.start(GUI_config.update_interval)

    def setup_stopped(self):
        if not any([box.running for box in self.setupboxes]):
            self.update_timer.stop()
            self.settings_groupbox.setEnabled(True)
            self.setups_groupbox.setEnabled(True)
            self.datadir_groupbox.setEnabled(True)

    def select_mode(self, mode):
        for box in self.setupboxes:
            box.select_mode(mode)

    def rate_text_change(self, text):
        if text:
            try:
                sampling_rate = int(text)
            except ValueError:
                self.rate_text.setText("")
                return
            for box in self.setupboxes:
                if box.board:
                    set_rate = box.board.set_sampling_rate(sampling_rate)
                    self.rate_text.setText(str(set_rate))

    def select_data_dir(self):
        self.data_dir_text.setText(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select data folder", self.data_dir)
        )

    def test_data_path(self):
        for box in self.setupboxes:
            box.test_data_path()

    def refresh(self):
        if self.GUI_main.ports_changed:
            for box in self.setupboxes:
                box.update_ports()

    def process_data(self):
        for box in self.setupboxes:
            if box.running:
                box.process_data()


# ----------------------------------------------------------------------------------------
#  Setupbox
# ----------------------------------------------------------------------------------------


class Setupbox(QtWidgets.QGroupBox):
    """Groupbox for displaying data from a single setup."""

    def __init__(self, parent, ID):
        super(QtWidgets.QGroupBox, self).__init__(parent=parent)
        self.multi_tab = self.parent()

        # Variables

        self.ID = ID
        self.board = None
        self.subject_ID = ""
        self.running = False
        self.connected = False
        self.clipboard = QtWidgets.QApplication.clipboard()  # Used to copy strings to computer clipboard.

        # Widgets

        self.status_label = QtWidgets.QLabel("Status:")
        self.status_text = QtWidgets.QLineEdit("Not connected")
        self.status_text.setStyleSheet("background-color:rgb(210, 210, 210);")
        self.status_text.setReadOnly(True)
        self.status_text.setFixedWidth(105)

        self.port_label = QtWidgets.QLabel("Serial port:")
        self.port_select = QtWidgets.QComboBox()
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.connect_button.setFixedWidth(110)
        self.connect_button.clicked.connect(lambda: self.disconnect() if self.connected else self.connect())

        self.subject_label = QtWidgets.QLabel("Subject ID:")
        self.subject_text = QtWidgets.QLineEdit(self.subject_ID)
        self.subject_text.setFixedWidth(80)
        self.subject_text.setMaxLength(12)
        self.subject_text.textChanged.connect(self.test_data_path)

        self.current_label_1 = QtWidgets.QLabel("LED 1 mA:")
        self.current_spinbox_1 = QtWidgets.QSpinBox()
        self.current_spinbox_1.setFixedWidth(50)
        self.current_label_2 = QtWidgets.QLabel("LED 2 mA:")
        self.current_spinbox_2 = QtWidgets.QSpinBox()
        self.current_spinbox_2.setFixedWidth(50)
        self.current_spinbox_1.setValue(GUI_config.default_LED_current[0])
        self.current_spinbox_2.setValue(GUI_config.default_LED_current[1])

        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setIcon(QtGui.QIcon("GUI/icons/play.svg"))
        self.record_button = QtWidgets.QPushButton("Record")
        self.record_button.setIcon(QtGui.QIcon("GUI/icons/record.svg"))
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setIcon(QtGui.QIcon("GUI/icons/stop.svg"))
        self.start_button.clicked.connect(self.start)
        self.record_button.clicked.connect(self.record)
        self.stop_button.clicked.connect(self.stop)

        # Plots

        self.analog_plot = Analog_plot(self)
        self.record_clock = Record_clock(self.analog_plot.axis)

        # Layout

        self.Hlayout = QtWidgets.QHBoxLayout()
        self.Hlayout.addWidget(self.status_text)
        self.Hlayout.addWidget(self.port_select)
        self.Hlayout.addWidget(self.connect_button)
        self.Hlayout.addWidget(self.subject_label)
        self.Hlayout.addWidget(self.subject_text)
        self.Hlayout.addWidget(self.current_label_1)
        self.Hlayout.addWidget(self.current_spinbox_1)
        self.Hlayout.addWidget(self.current_label_2)
        self.Hlayout.addWidget(self.current_spinbox_2)
        self.Hlayout.addWidget(self.start_button)
        self.Hlayout.addWidget(self.record_button)
        self.Hlayout.addWidget(self.stop_button)
        self.Hlayout.addStretch()
        self.Vlayout = QtWidgets.QVBoxLayout(self)
        self.Vlayout.addLayout(self.Hlayout)
        self.Vlayout.addWidget(self.analog_plot)

        # Initial setup.

        self.disconnect()  # Set initial state as disconnected.
        self.update_ports()

    # Button and box functions -------------------------------------------

    def connect(self):
        try:
            self.status_text.setText("Connecting")
            self.connect_button.setEnabled(False)
            self.multi_tab.GUI_main.app.processEvents()
            self.board = Acquisition_board(self.port_select.currentText())
            self.select_mode(self.multi_tab.mode_select.currentText())
            self.port_select.setEnabled(False)
            self.subject_text.setEnabled(True)
            self.current_spinbox_1.setEnabled(True)
            self.current_spinbox_2.setEnabled(True)
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            self.connect_button.setText("Disconnect")
            self.connect_button.setIcon(QtGui.QIcon("GUI/icons/disconnect.svg"))
            self.status_text.setText("Connected")
            self.connect_button.setEnabled(True)
            self.board.set_LED_current(self.current_spinbox_1.value(), self.current_spinbox_2.value())
            self.current_spinbox_1.valueChanged.connect(lambda v: self.board.set_LED_current(LED_1_current=int(v)))
            self.current_spinbox_2.valueChanged.connect(lambda v: self.board.set_LED_current(LED_2_current=int(v)))
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
        # Disconnect from pyboard.
        if self.board:
            self.board.close()
        self.board = None
        self.connect_button.setText("Connect")
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.status_text.setText("Not connected")
        self.connected = False
        self.port_select.setEnabled(True)
        self.subject_text.setEnabled(False)
        self.current_spinbox_1.setEnabled(False)
        self.current_spinbox_2.setEnabled(False)
        self.start_button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def test_data_path(self):
        # Checks whether data dir and subject ID are valid.
        self.data_dir = self.multi_tab.data_dir_text.text()
        self.subject_ID = self.subject_text.text()
        if self.running and os.path.isdir(self.data_dir) and str(self.subject_ID):
            self.record_button.setEnabled(True)
        else:
            self.record_button.setEnabled(False)

    def select_mode(self, mode):
        if self.board:
            self.board.set_mode(mode)
            self.multi_tab.rate_text.setText(str(self.board.sampling_rate))
            self.current_spinbox_1.setRange(0, self.board.max_LED_current)
            self.current_spinbox_2.setRange(0, self.board.max_LED_current)
            if self.current_spinbox_1.value() > self.board.max_LED_current:
                self.current_spinbox_1.setValue(self.board.max_LED_current)
                self.board.set_LED_current(LED_1_current=self.board.max_LED_current)
            if self.current_spinbox_2.value() > self.board.max_LED_current:
                self.current_spinbox_2.setValue(self.board.max_LED_current)
                self.board.set_LED_current(LED_2_current=self.board.max_LED_current)

    def select_data_dir(self):
        self.data_dir_text.setText(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select data folder", self.data_dir)
        )

    def start(self):
        # Reset plots.
        self.analog_plot.reset(self.board.sampling_rate)
        # Start acquisition.
        self.board.start()
        self.multi_tab.GUI_main.refresh_timer.stop()
        self.multi_tab.setup_started()
        self.running = True
        # Update UI.
        self.connect_button.setEnabled(False)
        self.start_button.setEnabled(False)
        if self.test_data_path():
            self.record_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_text.setText("Running")

    def record(self):
        if os.path.isdir(self.data_dir):
            filetype = self.multi_tab.filetype_select.currentText()
            file_name = self.board.record(self.multi_tab.data_dir, self.subject_ID, filetype)
            self.clipboard.setText(file_name)
            self.status_text.setText("Recording")
            self.current_spinbox_1.setEnabled(False)
            self.current_spinbox_2.setEnabled(False)
            self.record_button.setEnabled(False)
            self.subject_text.setEnabled(False)
            self.record_clock.start()
        else:
            self.data_dir_text.setText("Set valid directory")
            self.data_dir_label.setStyleSheet("color: rgb(255, 0, 0);")

    def stop(self, error=False):
        self.board.stop()
        self.running = False
        self.multi_tab.setup_stopped()
        self.stop_button.setEnabled(False)
        self.board.serial.reset_input_buffer()
        self.start_button.setEnabled(True)
        self.record_button.setEnabled(False)
        self.subject_text.setEnabled(True)
        if error:
            self.status_text.setText("Error")
        else:
            self.status_text.setText("Connected")
        self.record_clock.stop()

    def serial_connection_lost(self):
        if self.running:
            self.update_timer.stop()
            self.refresh_timer.start(self.refresh_interval)
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
        # Called regularly while running, read data from the serial port
        # and update the plot.
        try:
            data = self.board.process_data()
        except PyboardError:
            self.stop(error=True)
            raise
        if data:
            new_ADC1, new_ADC2, new_DI1, new_DI2 = data
            # Update plots.
            self.analog_plot.update(new_ADC1, new_ADC2)
            self.record_clock.update()

    def update_ports(self):
        self.port_select.clear()
        self.port_select.addItems(sorted(self.multi_tab.GUI_main.available_ports))

    # Cleanup.

    def closeEvent(self, event):
        # Called when GUI window is closed.
        if self.running:
            self.stop()
        if self.board:
            self.board.close()
        event.accept()
