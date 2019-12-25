from PyQt5 import QtGui, QtWidgets, QtCore
from connectionwrapper import ConnectionWrapper as CW
import ui_globaloptionsdialog
import configuration
import randomstring

class GlobalOptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(GlobalOptionsDialog, self).__init__(parent)

        self.ui = ui_globaloptionsdialog.Ui_GlobalOptionsDialog()
        self.ui.setupUi(self)

        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.saveButton.clicked.connect(CW(self.onSave))
        self.ui.generateButton.clicked.connect(CW(self.onGenerate))

        checkInterval = configuration.getAutoCheckIntervalMinutes()
        if checkInterval > 0:
            self.ui.reloadCheckbox.setChecked(True)
            self.ui.intervalSpinbox.setValue(checkInterval)
        else:
            self.ui.reloadCheckbox.setChecked(False)

        r = configuration.getAutoCheckReload()
        self.ui.reloadReallyRadio.setChecked(r)
        self.ui.reloadIndicateRadio.setChecked(not r)

        self.ui.sshCommandEdit.setText(configuration.getSshCommand())
        if configuration.getSshPassEnv():
            self.ui.sshPassEnvEdit.setText(configuration.getSshPassEnv())

        port = configuration.getTcpPort()
        if port > 0:
            self.ui.tcpServerCheckbox.setChecked(True)
            self.ui.tcpPortSpinbox.setValue(port)
        else:
            self.ui.tcpServerCheckbox.setChecked(False)

        if configuration.getAccessURL():
            self.ui.accessURLEdit.setText(configuration.getAccessURL())
        if configuration.getTcpPassPhrase():
            self.ui.aesKeyEdit.setText(configuration.getTcpPassPhrase())

    def onSave(self, checked):
        if self.ui.reloadCheckbox.isChecked():
            configuration.setAutoCheckIntervalMinutes(self.ui.intervalSpinbox.value())
        else:
            configuration.setAutoCheckIntervalMinutes(0)

        configuration.setAutoCheckReload(self.ui.reloadReallyRadio.isChecked())
        configuration.setSshCommand(self.ui.sshCommandEdit.text())
        configuration.setSshPassEnv(self.ui.sshPassEnvEdit.text())

        if self.ui.tcpServerCheckbox.isChecked():
            configuration.setTcpPort(self.ui.tcpPortSpinbox.value())
        else:
            configuration.setTcpPort(0)

        configuration.setAccessURL(self.ui.accessURLEdit.text())
        configuration.setTcpPassPhrase(self.ui.aesKeyEdit.text())

        self.accept()

    def onGenerate(self, checked):
        self.ui.accessURLEdit.setText(randomstring.getRandomString(16))
        self.ui.aesKeyEdit.setText(randomstring.getRandomString(16))

