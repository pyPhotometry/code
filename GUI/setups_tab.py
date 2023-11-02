import os
import json
from dataclasses import dataclass, asdict
from serial.tools import list_ports
from pyqtgraph.Qt import QtCore, QtWidgets

from GUI.acquisition_board import get_unique_id

setups_save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


class Setups_tab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.GUI_main = parent
        self.save_path = os.path.join(setups_save_dir, "setups.json")

        self.setups = {}  # {port: Setup} # Currently connected setups.
        self.saved_setups = self.load_setups_from_json()  # [Setup_info]
        self.setups_changed = True

        self.setups_table = QtWidgets.QTableWidget(0, 3, parent=self)
        self.setups_table.setHorizontalHeaderLabels(["Serial port", "Hardware ID", "Name"])
        self.setups_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.setups_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.setups_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.setups_table.verticalHeader().setVisible(False)
        self.vertical_layout = QtWidgets.QVBoxLayout(self)
        self.vertical_layout.addWidget(self.setups_table)
        self.vertical_layout.addStretch()

    def load_setups_from_json(self):
        if os.path.exists(self.save_path):
            with open(self.save_path, "r", encoding="utf-8") as f:
                setups_from_json = [Setup_info(**si_dict) for si_dict in json.loads(f.read())]
        else:
            setups_from_json = []
        return setups_from_json

    def get_saved_setup(self, unique_id=None, port=None):
        """Get a saved Setup_info object by unique_id or port."""
        if unique_id:
            try:  # Get setup with matching unique id if it exists.
                return next(si for si in self.saved_setups if si.unique_id == unique_id)
            except StopIteration:
                pass
        elif port:
            try:  # Get setup with matching port if it does not have a unique id.
                return next(si for si in self.saved_setups if si.port == port)
            except StopIteration:
                pass
        return None

    def setup_name_edited(self, setup):
        """Called when a setups name is edited to update saved setups."""
        saved_setup = self.get_saved_setup(unique_id=setup.unique_id, port=setup.port)
        if saved_setup:
            if not setup.name:  # Remove saved setup.
                self.saved_setups.remove(saved_setup)
            else:  # Update name.
                saved_setup.name = setup.name
        else:  # Create new saved setup.
            self.saved_setups.append(setup.get_info())
        self.setups_changed = True
        with open(self.save_path, "w", encoding="utf-8") as f:
            f.write(json.dumps([asdict(setup_info) for setup_info in self.saved_setups], indent=4))

    def refresh(self):
        """Called regularly when no task running to update tab with currently
        connected boards."""
        ports = set([c[0] for c in list_ports.comports() if ("Pyboard" in c[1]) or ("USB Serial Device" in c[1])])
        if not ports == self.setups.keys():
            # Add any newly connected setups.
            for port in set(ports) - set(self.setups.keys()):
                unique_id = get_unique_id(port)
                saved_setup = self.get_saved_setup(unique_id=unique_id, port=port)
                name = saved_setup.name if saved_setup else None
                self.setups[port] = Setup(self, port=port, unique_id=unique_id, name=name)
            # Remove any unplugged setups.
            for port in set(self.setups.keys()) - set(ports):
                self.setups[port].unplugged()
                del self.setups[port]
            self.setups_table.sortItems(0)
            self.setups_changed = True

    def get_setup_labels(self):
        """Return a list of GUI labels for non-hidden setups."""
        self.setups_changed = False
        return sorted([setup.label for setup in self.setups.values() if setup.name != "_hidden_"])

    def get_setup_port(self, label):
        """Get the serial port given the setup label."""
        return next(setup.port for setup in self.setups.values() if setup.label == label)


@dataclass
class Setup_info:
    port: str
    name: str = None
    unique_id: str = None


class Setup:
    def __init__(self, setups_tab, port=None, name=None, unique_id=None):
        self.setups_tab = setups_tab
        self.port = port
        self.name = name
        self.unique_id = unique_id
        self.label = self.name if self.name else self.port

        # GUI elements.
        self.port_item = QtWidgets.QTableWidgetItem()
        self.port_item.setText(port)
        self.port_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.name_edit = QtWidgets.QLineEdit()
        if self.name:
            self.name_edit.setText(self.name)
        self.name_edit.editingFinished.connect(self.name_changed)

        self.id_edit = QtWidgets.QLineEdit()
        self.id_edit.setReadOnly(True)
        if self.unique_id:
            self.id_edit.setText(str(self.unique_id)[:6])

        self.setups_tab.setups_table.insertRow(0)
        self.setups_tab.setups_table.setItem(0, 0, self.port_item)
        self.setups_tab.setups_table.setCellWidget(0, 1, self.id_edit)
        self.setups_tab.setups_table.setCellWidget(0, 2, self.name_edit)

    def name_changed(self):
        """Called when name text of setup is edited."""
        self.name = str(self.name_edit.text())
        self.label = self.name if self.name else self.port
        if self.name == "_hidden_":
            self.name_edit.setStyleSheet("color: grey;")
        else:
            self.name_edit.setStyleSheet("color: black;")
        self.setups_tab.setup_name_edited(self)

    def unplugged(self):
        """Called when a board is unplugged from computer to remove row from setups table."""
        self.setups_tab.setups_table.removeRow(self.port_item.row())

    def get_info(self):
        return Setup_info(name=self.name, unique_id=self.unique_id, port=self.port)
