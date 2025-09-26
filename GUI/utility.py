from pyqtgraph.Qt import QtCore


def set_cbox_item(cbox, item_name):
    """Set the selected item on a combobox by passing the item name.  If name is not
    valid then selected item is not changed."""
    index = cbox.findText(item_name, QtCore.Qt.MatchFlag.MatchFixedString)
    if index >= 0:
        cbox.setCurrentIndex(index)


def cbox_update_options(cbox, options):
    """Update the options available in a qcombobox without changing the selection."""
    selected = str(cbox.currentText())
    if selected:
        available = sorted(list(set([selected] + options)), key=str.lower)
        i = available.index(selected)
    else:  # cbox is currently empty.
        available = sorted(list(options), key=str.lower)
        i = 0
    cbox.clear()
    cbox.addItems(available)
    cbox.setCurrentIndex(i)
