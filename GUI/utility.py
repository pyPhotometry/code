from pyqtgraph import QtCore


def set_cbox_item(cbox, item_name):
    """Set the selected item on a combobox by passing the item name.  If name is not
    valid then selected item is not changed."""
    index = cbox.findText(item_name, QtCore.Qt.MatchFlag.MatchFixedString)
    if index >= 0:
        cbox.setCurrentIndex(index)
