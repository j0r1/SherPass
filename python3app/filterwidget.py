from PyQt5 import QtWidgets, QtCore, QtGui
from connectionwrapper import ConnectionWrapper as CW
import ui_filterwidget

class FilterWidget(QtWidgets.QWidget):

    filterChangedSignal = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super(FilterWidget, self).__init__(parent)

        self.ui = ui_filterwidget.Ui_FilterWidget()
        self.ui.setupUi(self)

        self.ui.filterText.textChanged.connect(CW(self.onFilterChanged))
        self.ui.filterText.textEdited.connect(CW(self.onFilterChanged))
        self.ui.filterText.escapePressedSignal.connect(CW(self.onEscapePressed))

    def setFocus(self):
        self.ui.filterText.setFocus()

    def onFilterChanged(self, txt):
        self.filterChangedSignal.emit(txt)

    def keyPressEvent(self, evt):
        QtWidgets.QApplication.instance().postEvent(self.ui.filterText, QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                                    evt.key(), evt.modifiers(), evt.text(), 
                                                                    evt.isAutoRepeat(), evt.count()))
        evt.accept()

    def onEscapePressed(self):
        self.ui.filterText.setText(" ")
        self.ui.filterText.setText("")
