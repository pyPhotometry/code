from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from dataclasses import dataclass, asdict


@dataclass
class Setup_info:
    port: str
    name: str


class Setups_tab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QtWidgets.QWidget, self).__init__(parent)

        self.setups_table = QtWidgets.QTableWidget(0, 2, parent=self)
        self.setups_table.setHorizontalHeaderLabels(["Serial port", "Name"])
        self.setups_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.setups_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        # self.setups_table.verticalHeader().setVisible(False)
        # self.setups_table.itemChanged.connect(lambda item: item.changed() if hasattr(item, "changed") else None)

        self.vertical_layout = QtWidgets.QVBoxLayout(self)
        self.vertical_layout.addWidget(self.setups_table)
        self.vertical_layout.addStretch()
