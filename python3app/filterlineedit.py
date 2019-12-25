from PyQt5 import QtWidgets, QtCore, QtGui

class FilterLineEdit(QtWidgets.QLineEdit):
    escapePressedSignal = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(FilterLineEdit, self).__init__(parent)

    def keyPressEvent(self, evt):
        super(FilterLineEdit, self).keyPressEvent(evt)
        if not evt.isAccepted():
            if evt.key() == QtCore.Qt.Key_Escape:
                self.escapePressedSignal.emit()

        # Make sure no events go back to the parent since that will
        # just cause the event to come back to us
        evt.accept()

