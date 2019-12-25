from PyQt5 import QtCore, QtWidgets
from connectionwrapper import ConnectionWrapper as CW
import ui_newpassworddialog
import copy

class NewPasswordDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(NewPasswordDialog, self).__init__(parent)

        self.ui = ui_newpassworddialog.Ui_NewPasswordDialog()
        self.ui.setupUi(self)

        self.ui.okButton.clicked.connect(CW(self.onOk))
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.showCheckBox.clicked.connect(CW(self.onPasswordShowClicked))
        self.password = None

    def onOk(self, checked):
        pass1 = self.ui.passwordEdit.text()
        pass2 = self.ui.passwordRepeatEdit.text()
        if len(pass1) < 7:
            QtWidgets.QMessageBox.warning(self, "Bad length", "Password length must be at least 7 characters")
            return

        if pass1 != pass2:
            QtWidgets.QMessageBox.warning(self, "Bad match", "Entered passwords are not the same")
            return

        self.password = pass1
        self.accept()

    def onPasswordShowClicked(self, checked):
        mode = QtWidgets.QLineEdit.Normal if self.ui.showCheckBox.checkState() == QtCore.Qt.Checked else QtWidgets.QLineEdit.Password
        self.ui.passwordEdit.setEchoMode(mode)

    def getPassword(self):
        return self.password

