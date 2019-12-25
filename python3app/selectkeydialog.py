from PyQt5 import QtWidgets, QtCore, QtGui
import ui_selectkeydialog
import copy

class SelectKeyDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(SelectKeyDialog, self).__init__(parent)

        self.ui = ui_selectkeydialog.Ui_SelectKeyDialog()
        self.ui.setupUi(self)
        self.keys = [ ]

    def setAvailableKeys(self, keys):
        self.keys = copy.deepcopy(keys)
        for k in self.keys:
            self.ui.keyCombo.addItem("{} ({})".format(k[0], k[1]))
    
    def getSelectedFingerprint(self):
        idx = self.ui.keyCombo.currentIndex()
        if idx < 0:
            return None
        return self.keys[idx][1]
