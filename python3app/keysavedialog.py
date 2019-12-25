from PyQt5 import QtWidgets, QtCore, QtGui
import ui_keysavedialog
from connectionwrapper import ConnectionWrapper as CW
from sherpassexception import SherPassException

class KeySaveDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(KeySaveDialog, self).__init__(parent)

        self.ui = ui_keysavedialog.Ui_KeySaveDialog()
        self.ui.setupUi(self)

        self.ui.cancelButton.clicked.connect(CW(self.onCancel))
        self.ui.saveButton.clicked.connect(CW(self.onSave))
        self.ui.browseButton.clicked.connect(CW(self.onBrowse))

        self.fileName = None

    def onSave(self, checked):
        try:
            if self.ui.saveSherPassRadio.isChecked():
                fileName = self.ui.sherpNameEdit.text()
                if not fileName:
                    raise SherPassException("No file name specified")

                self.fileName = fileName

            elif self.ui.saveArbitraryRadio.isChecked():
                fileName = self.ui.generalNameEdit.text()
                if not fileName:
                    raise SherPassException("No file name specified")

                self.fileName = fileName

            else:
                raise SherPassException("Internal error: no known option selected")

            self.accept()
        except SherPassException as e:
            QtWidgets.QMessageBox.warning(self, "Error specifing save file", "Error specifing save file:\n{}".format(str(e)))

    def onCancel(self, checked):
        if QtWidgets.QMessageBox.question(self, "Sure?", "Are you really sure you want to discard the generated key?",
                                             QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, 
                                             QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        self.reject()

    def onBrowse(self, checked):
        fileName, filterName = QtWidgets.QFileDialog.getSaveFileName(self, "Specify save file for key", filter = "Private key files (*.privkey)")
        if not fileName: # cancelled
            return

        self.ui.generalNameEdit.setText(fileName)

    def closeEvent(self, e):
        e.ignore()

    # Make sure escape doesn't close the dialog
    def keyPressEvent(self, e):
        e.accept()

    def getFileName(self):
        return self.fileName[:]
