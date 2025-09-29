import json
from pathlib import Path
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from pyqtgraph.Qt.QtWidgets import QFrame, QMessageBox
from serial import SerialException
from dataclasses import dataclass, asdict
from typing import List
from enum import Enum

import config.GUI_config as GUI_config
from GUI.acquisition_board import Acquisition_board
from GUI.pyboard import PyboardError
from GUI.plotting import Signals_plot
from GUI.dir_paths import experiments_dir, data_dir, config_dir
from GUI.utility import set_cbox_item, cbox_update_options

AlignVCenter = QtCore.Qt.AlignmentFlag.AlignVCenter

# ----------------------------------------------------------------------------------------
#  Acquisition_tab
# ----------------------------------------------------------------------------------------


@dataclass
class Setup_config:
    port: str
    subject_ID: str
    LED_1_current: int
    LED_2_current: int


@dataclass
class Multitab_config:
    n_setups: int
    mode: str
    sampling_rate: int
    sync_out: bool
    data_dir: str
    file_type: str
    setup_configs: List[Setup_config]


class Status(Enum):
    DISCONNECTED = 0
    STOPPED = 1
    RUNNING = 2
    RECORDING = 3
    MIXED_RUNNING = 4
    MIXED_NOTRUNNING = 5


class Acquisition_tab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.GUI_main = self.parent()
        self.setups_tab = self.GUI_main.setups_tab

        # Variables.
        self.status = None
        self.control_button_action = None
        self.setupboxes = []
        self.n_setups = 0
        self.data_dir = data_dir
        self.saved_config = None
        self.config_save_path = None

        # Config groupbox

        self.config_groupbox = QtWidgets.QGroupBox("Config")
        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.setIcon(QtGui.QIcon("GUI/icons/save.svg"))
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setEnabled(False)
        self.save_as_button = QtWidgets.QPushButton("Save as")
        self.save_as_button.setIcon(QtGui.QIcon("GUI/icons/save_as.svg"))
        self.save_as_button.clicked.connect(self.save_config_as)
        self.load_button = QtWidgets.QPushButton("Load")
        self.load_button.clicked.connect(self.load_config)
        self.setups_label = QtWidgets.QLabel("Setups:")
        self.setups_spinbox = QtWidgets.QSpinBox()
        self.setups_spinbox.setFixedWidth(40)
        self.setups_spinbox.setRange(1, 9)
        self.setups_spinbox.valueChanged.connect(self.add_remove_setups)

        self.configgroup_layout = QtWidgets.QHBoxLayout()
        self.configgroup_layout.addWidget(self.save_button)
        self.configgroup_layout.addWidget(self.save_as_button)
        self.configgroup_layout.addWidget(self.load_button)
        self.configgroup_layout.addWidget(self.setups_label)
        self.configgroup_layout.addWidget(self.setups_spinbox)
        self.config_groupbox.setLayout(self.configgroup_layout)

        # Settings groupbox.

        self.settings_groupbox = QtWidgets.QGroupBox("Acquisition settings")

        self.mode_label = QtWidgets.QLabel("Mode:")
        self.mode_select = QtWidgets.QComboBox()
        self.mode_select.addItems(GUI_config.available_acquisition_modes)
        set_cbox_item(self.mode_select, GUI_config.default_acquisition_mode)
        self.mode_select.currentTextChanged[str].connect(self.select_mode)
        self.rate_label = QtWidgets.QLabel("Sampling rate (Hz):")
        self.rate_spinbox = QtWidgets.QSpinBox()
        self.rate_spinbox.setFixedWidth(50)
        self.sync_out_label = QtWidgets.QLabel("Sync-out:")
        self.sync_out_checkbox = QtWidgets.QCheckBox()
        self.sync_out_checkbox.stateChanged.connect(self.toggle_sync_out)

        self.settingsgroup_layout = QtWidgets.QHBoxLayout()
        self.settingsgroup_layout.addWidget(self.mode_label, alignment=AlignVCenter)
        self.settingsgroup_layout.addWidget(self.mode_select, alignment=AlignVCenter)
        self.settingsgroup_layout.addWidget(self.rate_label, alignment=AlignVCenter)
        self.settingsgroup_layout.addWidget(self.rate_spinbox, alignment=AlignVCenter)
        self.settingsgroup_layout.addWidget(self.sync_out_label, alignment=AlignVCenter)
        self.settingsgroup_layout.addWidget(self.sync_out_checkbox, alignment=AlignVCenter)
        self.settingsgroup_layout.addStretch()
        self.settings_groupbox.setLayout(self.settingsgroup_layout)

        # Data directory groupbox

        self.datadir_groupbox = QtWidgets.QGroupBox("Data directory")

        self.data_dir_text = QtWidgets.QLineEdit(str(self.data_dir))
        self.data_dir_button = QtWidgets.QPushButton("")
        self.data_dir_button.setIcon(QtGui.QIcon("GUI/icons/folder.svg"))
        self.data_dir_button.setFixedWidth(30)
        self.filetype_label = QtWidgets.QLabel("File type:")
        self.filetype_select = QtWidgets.QComboBox()
        self.filetype_select.addItems(["ppd", "csv"])
        set_cbox_item(self.filetype_select, GUI_config.default_filetype)

        self.filegroup_layout = QtWidgets.QHBoxLayout()
        self.filegroup_layout.addWidget(self.data_dir_text)
        self.filegroup_layout.addWidget(self.data_dir_button)
        self.filegroup_layout.addWidget(self.filetype_label)
        self.filegroup_layout.addWidget(self.filetype_select)
        self.datadir_groupbox.setLayout(self.filegroup_layout)

        self.data_dir_text.textChanged.connect(self.test_data_path)
        self.data_dir_button.clicked.connect(self.select_data_dir)

        # Controls groupbox

        self.controls_groupbox = QtWidgets.QGroupBox("Control all")

        self.connect_all_button = QtWidgets.QPushButton()
        self.connect_all_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.connect_all_button.clicked.connect(
            lambda: self.connect() if self.status == Status.DISCONNECTED else self.disconnect()
        )

        self.start_all_button = QtWidgets.QPushButton()
        self.start_all_button.setIcon(QtGui.QIcon("GUI/icons/play.svg"))
        self.start_all_button.clicked.connect(self.start)

        self.record_all_button = QtWidgets.QPushButton()
        self.record_all_button.setIcon(QtGui.QIcon("GUI/icons/record.svg"))
        self.record_all_button.clicked.connect(self.record)

        self.stop_all_button = QtWidgets.QPushButton()
        self.stop_all_button.setIcon(QtGui.QIcon("GUI/icons/stop.svg"))
        self.stop_all_button.clicked.connect(self.stop)

        self.controlgroup_layout = QtWidgets.QHBoxLayout()
        self.controlgroup_layout.addWidget(self.connect_all_button)
        self.controlgroup_layout.addWidget(self.start_all_button)
        self.controlgroup_layout.addWidget(self.record_all_button)
        self.controlgroup_layout.addWidget(self.stop_all_button)
        self.controls_groupbox.setLayout(self.controlgroup_layout)

        # Layout

        self.scroll_area = QtWidgets.QScrollArea(parent=self)
        self.scroll_area.horizontalScrollBar().setEnabled(False)
        self.scroll_inner = QtWidgets.QFrame(self)
        self.boxes_layout = QtWidgets.QVBoxLayout(self.scroll_inner)
        self.scroll_area.setWidget(self.scroll_inner)
        self.scroll_area.setWidgetResizable(True)

        self.v_layout = QtWidgets.QVBoxLayout(self)
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(self.config_groupbox)
        self.h_layout.addWidget(self.settings_groupbox)
        self.h_layout.addWidget(self.controls_groupbox)
        self.v_layout.addLayout(self.h_layout)
        self.v_layout.addWidget(self.datadir_groupbox)
        self.v_layout.addWidget(self.scroll_area)

        # Timers.

        self.update_timer = QtCore.QTimer()  # Timer to regularly call process_data()
        self.update_timer.timeout.connect(self.process_data)

        # Initial state

        self.select_mode(self.mode_select.currentText())
        self.toggle_sync_out()
        self.add_remove_setups(1)
        self.update_status()

    # Methods to change number of setups.

    def add_setup(self):
        self.setupboxes.append(Setupbox(self, ID=len(self.setupboxes)))
        self.boxes_layout.addWidget(self.setupboxes[-1])
        self.n_setups = len(self.setupboxes)

    def remove_setup(self):
        box = self.setupboxes.pop(-1)
        box.close()
        box.setParent(None)
        box.deleteLater()
        self.n_setups = len(self.setupboxes)

    def add_remove_setups(self, n_setups):
        while not (self.n_setups == n_setups):
            if self.n_setups > n_setups:
                self.remove_setup()
            elif self.n_setups < n_setups:
                self.add_setup()
        if self.n_setups == 1:  # Show event triggered plot.
            self.setupboxes[0].signals_plot.etp_checkbox.setChecked(True)
        else:
            self.setupboxes[0].signals_plot.etp_checkbox.setChecked(False)
        self.update_status()

    # Methods to update the UI

    def update_status(self):
        """Called when the status of a setup changes to update the tab status"""
        box_states = [box.status for box in self.setupboxes]
        status_set = set(box_states)
        if len(status_set) == 1:
            new_status = status_set.pop()
        elif any([bs in (Status.RUNNING, Status.RECORDING) for bs in box_states]):
            new_status = Status.MIXED_RUNNING
        else:
            new_status = Status.MIXED_NOTRUNNING
        # Update UI
        if new_status != self.status:
            if new_status in (Status.RUNNING, Status.RECORDING, Status.MIXED_RUNNING):  # Setups are running.
                self.config_groupbox.setEnabled(False)
                self.settings_groupbox.setEnabled(False)
                self.datadir_groupbox.setEnabled(False)
                self.GUI_main.tab_widget.setTabEnabled(1, False)
                if not self.update_timer.isActive():
                    self.update_timer.start(GUI_config.update_interval)
            else:  # No setups running.
                self.update_timer.stop()
                self.config_groupbox.setEnabled(True)
                self.settings_groupbox.setEnabled(True)
                self.datadir_groupbox.setEnabled(True)
                self.GUI_main.tab_widget.setTabEnabled(1, True)
            if new_status in (Status.MIXED_NOTRUNNING, Status.MIXED_RUNNING):
                self.controls_groupbox.setEnabled(False)
            else:
                self.controls_groupbox.setEnabled(True)
            if new_status == Status.DISCONNECTED:
                self.connect_all_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
                self.connect_all_button.setEnabled(True)
                self.start_all_button.setEnabled(False)
                self.record_all_button.setEnabled(False)
                self.stop_all_button.setEnabled(False)
            elif new_status == Status.STOPPED:
                self.connect_all_button.setIcon(QtGui.QIcon("GUI/icons/disconnect.svg"))
                self.connect_all_button.setEnabled(True)
                self.start_all_button.setEnabled(True)
                self.record_all_button.setEnabled(False)
                self.stop_all_button.setEnabled(False)
            elif new_status == Status.RUNNING:
                self.connect_all_button.setEnabled(False)
                self.start_all_button.setEnabled(False)
                self.test_data_path()
                self.stop_all_button.setEnabled(True)
            elif new_status == Status.RECORDING:
                self.connect_all_button.setEnabled(False)
                self.start_all_button.setEnabled(False)
                self.record_all_button.setEnabled(False)
                self.stop_all_button.setEnabled(True)
        self.status = new_status

    # Methods to apply operation to all setups.

    def connect(self):
        for box in self.setupboxes:
            box.connect()

    def start(self):
        for box in self.setupboxes:
            box.start()

    def record(self):
        if not self.check_unique_subject_IDs():
            return
        for box in self.setupboxes:
            box.record(IDs_checked=True)

    def stop(self):
        for box in self.setupboxes:
            box.stop()

    def disconnect(self):
        for box in self.setupboxes:
            box.disconnect()

    def select_mode(self, mode):
        max_sampling_rate = self.setups_tab.get_max_sampling_rate(mode)
        self.rate_spinbox.setRange(0, max_sampling_rate)
        self.rate_spinbox.setValue(max_sampling_rate)
        for box in self.setupboxes:
            box.select_mode(mode)

    def set_full_Yscale(self):
        for box in self.setupboxes:
            box.signals_plot.fullscale()

    def set_auto_Yscale(self):
        for box in self.setupboxes:
            box.signals_plot.autoscale()

    def toggle_demean_mode(self):
        for box in self.setupboxes:
            box.signals_plot.demean_checkbox.setChecked(not box.signals_plot.demean_checkbox.isChecked())

    def toggle_sync_out(self):
        if self.sync_out_checkbox.isChecked():
            with open(Path(config_dir, "sync_out_config.json"), "r") as file:
                self.sync_out_config = json.load(file)
            for box in self.setupboxes:
                box.signals_plot.etp_checkbox.setChecked(False)
                box.signals_plot.etp_checkbox.setEnabled(False)
        else:
            self.sync_out_config = False
            for box in self.setupboxes:
                box.signals_plot.etp_checkbox.setEnabled(True)

    # Data path methods.

    def select_data_dir(self):
        """Open a dialog to select the data directory"""
        self.data_dir_text.setText(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select data folder", str(self.data_dir))
        )

    def test_data_path(self):
        """Test whether all setups have a valid data path."""
        self.data_dir = Path(self.data_dir_text.text())
        all_paths_OK = all([box.test_data_path() for box in self.setupboxes])
        if all_paths_OK:
            self.record_all_button.setEnabled(True)
        else:
            self.record_all_button.setEnabled(False)
        return all_paths_OK

    def get_config(self):
        """Get the configuation of the tab as a Multitab_config object"""
        return Multitab_config(
            n_setups=self.setups_spinbox.value(),
            mode=self.mode_select.currentText(),
            sampling_rate=self.rate_spinbox.value(),
            sync_out=self.sync_out_checkbox.isChecked(),
            data_dir=self.data_dir_text.text(),
            file_type=self.filetype_select.currentText(),
            setup_configs=[box.get_config() for box in self.setupboxes],
        )

    def check_unique_subject_IDs(self):
        """Check all subject IDs are unique and display warning dialog if not."""
        subject_IDs = [box.subject_ID for box in self.setupboxes if box.subject_ID]
        repeated_IDs = [subject_ID for subject_ID in set(subject_IDs) if subject_IDs.count(subject_ID) > 1]
        if repeated_IDs:
            QMessageBox.warning(
                None,
                "Duplicate subject ID",
                "All subject IDs must be unique. Duplicate subject IDs:\n\n" + ", ".join(repeated_IDs),
            )
            return False
        else:
            return True

    # Load and save tab configuration.

    def set_config(self, multitab_config):
        """Set the configuration of the tab from a Multitab_config object"""
        self.setups_spinbox.setValue(multitab_config.n_setups)
        self.mode_select.setCurrentIndex(self.mode_select.findText(multitab_config.mode))
        self.rate_spinbox.setValue(multitab_config.sampling_rate)
        self.sync_out_checkbox.setChecked(multitab_config.sync_out)
        self.data_dir_text.setText(multitab_config.data_dir)
        self.filetype_select.setCurrentIndex(self.filetype_select.findText(multitab_config.file_type))
        for box, setup_config_dict in zip(self.setupboxes, multitab_config.setup_configs):
            box.set_config(Setup_config(**setup_config_dict))

    def save_config(self):
        """Save tab configuration to already selected save file."""
        self.saved_config = self.get_config()
        with open(self.config_save_path, "w", encoding="utf-8") as save_file:
            save_file.write(json.dumps(asdict(self.saved_config), sort_keys=True, indent=4))
        self.save_button.setEnabled(False)

    def save_config_as(self):
        """Open dialog to select file to save tab configuration as a json file"""
        new_path = QtWidgets.QFileDialog.getSaveFileName(self, "", str(experiments_dir), ("JSON files (*.json)"))[0]
        if not new_path:
            return
        self.config_save_path = new_path
        self.saved_config = self.get_config()
        with open(self.config_save_path, "w", encoding="utf-8") as save_file:
            save_file.write(json.dumps(asdict(self.saved_config), sort_keys=True, indent=4))
        self.save_button.setEnabled(False)

    def load_config(self):
        """Load tab configuration from json file"""
        new_path = QtWidgets.QFileDialog.getOpenFileName(self, "", str(experiments_dir), ("JSON files (*.json)"))[0]
        if not new_path:
            return
        self.config_save_path = new_path
        self.disconnect()
        with open(self.config_save_path, "r", encoding="utf-8") as load_file:
            new_config = Multitab_config(**json.loads(load_file.read()))
        self.set_config(new_config)
        self.saved_config = self.get_config()
        self.save_button.setEnabled(False)

    # Timer callbacks

    def refresh(self):
        """Called regularly when no setups are running"""
        # Handle connected/disconnected setups.
        if self.setups_tab.setups_changed:
            setup_labels = self.setups_tab.get_setup_labels()
            for box in self.setupboxes:
                box.update_setups(setup_labels)
        # Enable/disable save button.
        if self.saved_config != self.get_config() and self.config_save_path:
            self.save_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)

    def process_data(self):
        """Called regularly while setups are running to process new data."""
        for box in self.setupboxes:
            if box.is_running():
                box.process_data()


# ----------------------------------------------------------------------------------------
#  Setupbox
# ----------------------------------------------------------------------------------------


class Setupbox(QtWidgets.QFrame):
    """Widget for displaying data from a single setup."""

    def __init__(self, parent, ID):
        super(QtWidgets.QFrame, self).__init__(parent=parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel | QtWidgets.QFrame.Shadow.Plain)
        self.acquisition_tab = self.parent()
        self.setups_tab = self.acquisition_tab.GUI_main.setups_tab

        # Variables

        self.status = Status.DISCONNECTED
        self.ID = ID
        self.board = None
        self.subject_ID = ""
        self.clipboard = QtWidgets.QApplication.clipboard()  # Used to copy strings to computer clipboard.

        # Widgets

        self.status_text = QtWidgets.QLineEdit("Not connected")
        self.status_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_text.setReadOnly(True)
        self.status_text.setFixedWidth(105)

        self.port_select = QtWidgets.QComboBox()
        self.port_select.setPlaceholderText("Select setup")
        self.port_select.setFixedWidth(100)
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.connect_button.setFixedWidth(110)
        self.connect_button.clicked.connect(
            lambda: self.connect() if self.status == Status.DISCONNECTED else self.disconnect()
        )

        self.subject_label = QtWidgets.QLabel("Subject ID:")
        self.subject_text = QtWidgets.QLineEdit(self.subject_ID)
        self.subject_text.textChanged.connect(self.acquisition_tab.test_data_path)

        self.current_label_1 = QtWidgets.QLabel("LED current (mA) Ch1:")
        self.current_spinbox_1 = QtWidgets.QSpinBox()
        self.current_spinbox_1.setFixedWidth(50)
        self.current_label_2 = QtWidgets.QLabel("Ch2:")
        self.current_spinbox_2 = QtWidgets.QSpinBox()
        self.current_spinbox_2.setFixedWidth(50)
        self.current_spinbox_1.setRange(0, 999)
        self.current_spinbox_2.setRange(0, 999)
        self.current_spinbox_1.setValue(GUI_config.default_LED_current[0])
        self.current_spinbox_2.setValue(GUI_config.default_LED_current[1])

        self.start_button = QtWidgets.QPushButton()
        self.start_button.setIcon(QtGui.QIcon("GUI/icons/play.svg"))
        self.record_button = QtWidgets.QPushButton()
        self.record_button.setIcon(QtGui.QIcon("GUI/icons/record.svg"))
        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setIcon(QtGui.QIcon("GUI/icons/stop.svg"))
        self.start_button.clicked.connect(self.start)
        self.record_button.clicked.connect(self.record)
        self.stop_button.clicked.connect(self.stop)

        # Plots

        self.signals_plot = Signals_plot(self)

        # Layout

        self.Hlayout = QtWidgets.QHBoxLayout()
        self.Hlayout.addWidget(self.status_text)
        self.Hlayout.addWidget(self.port_select)
        self.Hlayout.addWidget(self.connect_button)
        self.Hlayout.addWidget(QFrame(frameShape=QFrame.Shape.VLine, frameShadow=QFrame.Shadow.Sunken))
        self.Hlayout.addWidget(self.subject_label)
        self.Hlayout.addWidget(self.subject_text)
        self.Hlayout.addWidget(QFrame(frameShape=QFrame.Shape.VLine, frameShadow=QFrame.Shadow.Sunken))
        self.Hlayout.addWidget(self.current_label_1)
        self.Hlayout.addWidget(self.current_spinbox_1)
        self.Hlayout.addWidget(self.current_label_2)
        self.Hlayout.addWidget(self.current_spinbox_2)
        self.Hlayout.addWidget(QFrame(frameShape=QFrame.Shape.VLine, frameShadow=QFrame.Shadow.Sunken))
        self.Hlayout.addWidget(self.start_button)
        self.Hlayout.addWidget(self.record_button)
        self.Hlayout.addWidget(self.stop_button)
        self.Vlayout = QtWidgets.QVBoxLayout(self)
        self.Vlayout.addLayout(self.Hlayout)
        self.Vlayout.addWidget(QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken))
        self.Vlayout.addWidget(self.signals_plot)

        # Initial setup.

        self.disconnect()  # Set initial state as disconnected.
        self.update_setups(self.setups_tab.get_setup_labels())
        self.select_first_available_setup()

    # Button and box methods

    def connect(self):
        """Connect to a pyboard."""
        try:
            setup = self.setups_tab.get_setup_by_label(self.port_select.currentText())
            if not setup:
                self.status_text.setText("Connection failed")
                return
            serial_port = setup.port
            if not setup.device_type:
                setup.open_device_select_dialog()
            device_config = self.setups_tab.device_configs[setup.device_type]

            self.status_text.setText("Connecting")
            self.connect_button.setEnabled(False)
            self.acquisition_tab.GUI_main.app.processEvents()
            self.board = Acquisition_board(serial_port, device_config)
            self.select_mode(self.acquisition_tab.mode_select.currentText())
            self.board.set_sampling_rate(self.acquisition_tab.rate_spinbox.value())
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
            self.status = Status.STOPPED
            self.acquisition_tab.update_status()
        except SerialException:
            self.status_text.setText("Connection failed")
            self.connect_button.setEnabled(True)
            raise
        except PyboardError:
            self.status_text.setText("Connection failed")
            self.connect_button.setEnabled(True)
            try:
                self.board.close()
            except AttributeError:
                pass
            raise

    def disconnect(self):
        """Disconnect from pyboard."""
        if self.is_running():
            self.stop()
        if self.board:
            self.board.close()
        self.status = Status.DISCONNECTED
        self.acquisition_tab.update_status()
        self.board = None
        self.connect_button.setText("Connect")
        self.connect_button.setIcon(QtGui.QIcon("GUI/icons/connect.svg"))
        self.status_text.setText("Not connected")
        self.port_select.setEnabled(True)
        self.subject_text.setEnabled(False)
        self.start_button.setEnabled(False)
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.current_spinbox_1.setEnabled(False)
        self.current_spinbox_2.setEnabled(False)

    def start(self):
        """Start data acqusition"""
        # self.select_mode(self.acquisition_tab.mode_select.currentText())
        self.board.set_sampling_rate(self.acquisition_tab.rate_spinbox.value())
        self.signals_plot.reset(self.board.sampling_rate)
        self.board.start(self.acquisition_tab.sync_out_config)
        self.status = Status.RUNNING
        self.acquisition_tab.update_status()
        # Update UI.
        self.connect_button.setEnabled(False)
        self.start_button.setEnabled(False)
        if self.test_data_path():
            self.record_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_text.setText("Running")
        self.signals_plot.info_overlay.start_acquisition()

    def record(self, IDs_checked=False):
        """Start recording data to disk."""
        if not (IDs_checked or self.acquisition_tab.check_unique_subject_IDs()):
            return
        filetype = self.acquisition_tab.filetype_select.currentText()
        file_name = self.board.record(self.acquisition_tab.data_dir, self.subject_ID, filetype)
        self.clipboard.setText(file_name)
        self.status_text.setText("Recording")
        self.current_spinbox_1.setEnabled(False)
        self.current_spinbox_2.setEnabled(False)
        self.record_button.setEnabled(False)
        self.subject_text.setEnabled(False)
        self.signals_plot.info_overlay.start_recording()
        self.status = Status.RECORDING
        self.acquisition_tab.update_status()

    def stop(self):
        """Stop data acqusition"""
        try:
            self.board.stop()
        except:  # Called for UI effects after board error.
            pass
        self.status = Status.STOPPED
        self.acquisition_tab.update_status()
        self.stop_button.setEnabled(False)
        self.board.serial.reset_input_buffer()
        self.start_button.setEnabled(True)
        self.record_button.setEnabled(False)
        self.current_spinbox_1.setEnabled(True)
        self.current_spinbox_2.setEnabled(True)
        self.subject_text.setEnabled(True)
        self.connect_button.setEnabled(True)
        self.status_text.setText("Connected")
        self.signals_plot.info_overlay.stop_recording()

    # Configuration

    def test_data_path(self):
        """Checks whether data dir and subject ID are valid."""
        self.subject_ID = self.subject_text.text()
        if self.status == Status.RUNNING and self.acquisition_tab.data_dir.exists() and str(self.subject_ID):
            self.record_button.setEnabled(True)
            return True
        else:
            self.record_button.setEnabled(False)
            return False

    def select_mode(self, mode):
        """Set the acqusition mode."""
        if self.board and not (self.board.mode == mode):
            self.board.set_mode(mode)
            self.current_spinbox_1.setRange(0, self.board.max_LED_current)
            self.current_spinbox_2.setRange(0, self.board.max_LED_current)
            if self.current_spinbox_1.value() > self.board.max_LED_current:
                self.current_spinbox_1.setValue(self.board.max_LED_current)
                self.board.set_LED_current(LED_1_current=self.board.max_LED_current)
            if self.current_spinbox_2.value() > self.board.max_LED_current:
                self.current_spinbox_2.setValue(self.board.max_LED_current)
                self.board.set_LED_current(LED_2_current=self.board.max_LED_current)
            self.signals_plot.set_n_signals(self.board.n_analog_signals)

    def get_config(self):
        """Return the current configuration of the Setupbox as a Setup_config object"""
        return Setup_config(
            port=self.port_select.currentText(),
            subject_ID=self.subject_text.text(),
            LED_1_current=self.current_spinbox_1.value(),
            LED_2_current=self.current_spinbox_2.value(),
        )

    def set_config(self, setup_config):
        """Set the Setupbox configuration from a Setup_config object"""
        self.port_select.setCurrentIndex(self.port_select.findText(setup_config.port))
        self.subject_text.setText(setup_config.subject_ID)
        self.current_spinbox_1.setValue(setup_config.LED_1_current)
        self.current_spinbox_2.setValue(setup_config.LED_2_current)

    def is_running(self):
        return True if self.status in (Status.RUNNING, Status.RECORDING) else False

    # Timer callbacks.

    def process_data(self):
        # Called regularly while running, read data from the serial port
        # and update the plot.
        try:
            new_data = self.board.process_data()
        except (PyboardError, SerialException):
            self.disconnect()
            self.status_text.setText("Error")
            raise
            return
        if new_data:  # Update plots.
            self.signals_plot.update(new_data)

    def update_setups(self, setup_labels):
        """Update available ports in port_select combobox."""
        cbox_update_options(self.port_select, setup_labels)

    def select_first_available_setup(self):
        """Set the port_select to the first available setup given setups assiged to other setupboxes."""
        assigned_setups = [box.port_select.currentText() for box in self.acquisition_tab.setupboxes if box is not self]
        try:
            set_cbox_item(
                self.port_select, next(sl for sl in self.setups_tab.get_setup_labels() if sl not in assigned_setups)
            )
        except StopIteration:
            self.port_select.setCurrentIndex(-1)

    # Cleanup.

    def close(self):
        # Stop acqusition and disconnect.
        if self.is_running():
            self.stop()
        if self.board:
            self.board.close()

    def closeEvent(self, event):
        # Called when GUI window is closed.
        self.close()
        event.accept()
