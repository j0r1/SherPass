from PyQt5 import QtCore, QtGui, QtWidgets
import ui_directoriesdialog
from connectionwrapper import ConnectionWrapper as CW

class DirectoriesDialog(QtWidgets.QDialog):
    def __init__(self, parent, info = None):
        super(DirectoriesDialog, self).__init__(parent)

        self.ui = ui_directoriesdialog.Ui_DirectoriesDialog()
        self.ui.setupUi(self)

        if info:
            self.ui.infoLabel.setText(info)
        else:
            self.ui.infoLabel.hide()

        self.ui.defaultDirCheckbox.toggled.connect(CW(self.slotDefaultDirToggled))
        self.ui.privkeyBrowseButton.clicked.connect(CW(self.onBrowsrPrivateKeyDir))
        self.ui.pubkeyBrowseButton.clicked.connect(CW(self.onBrowsePublicKeyDir))
        self.ui.passBrowseButton.clicked.connect(CW(self.onBrowsePassDir))

        self.setUseDefaultPrivateKeyDir(True)

    def setUseDefaultPrivateKeyDir(self, f):
        if f:
            self.ui.defaultDirCheckbox.setChecked(True)
            self.ui.privkeyDirLabel.hide()
            self.ui.privkeyDirEdit.hide()
            self.ui.privkeyBrowseButton.hide()
        else:
            self.ui.defaultDirCheckbox.setChecked(False)
            self.ui.privkeyDirLabel.show()
            self.ui.privkeyDirEdit.show()
            self.ui.privkeyBrowseButton.show()

    def slotDefaultDirToggled(self, checked):
        self.setUseDefaultPrivateKeyDir(checked)

    def useDefaultPrivateKeyDir(self):
        return self.ui.defaultDirCheckbox.isChecked()

    def getPrivateKeyDir(self):
        return self.ui.privkeyDirEdit.text()

    def getPublicKeyDir(self):
        return self.ui.pubkeyDirEdit.text()

    def getPasswordEntryDir(self):
        return self.ui.passDirEdit.text()

    def onBrowse(self, widget, mode):
        dlg = QtWidgets.QFileDialog()
        if mode:
            dlg.setFileMode(mode)

        initialDir = widget.text()
        if len(initialDir) > 0: 
            dlg.setDirectory(initialDir)

        if dlg.exec_():
            f = dlg.selectedFiles()
            if f:
                widget.setText(f[0])

    def onBrowsePublicKeyDir(self, checked):
        self.onBrowse(self.ui.pubkeyDirEdit, QtWidgets.QFileDialog.Directory)

    def onBrowsePassDir(self, checked):
        self.onBrowse(self.ui.passDirEdit, QtWidgets.QFileDialog.Directory)

    def onBrowsrPrivateKeyDir(self, checked):
        self.onBrowse(self.ui.privkeyDirEdit, QtWidgets.QFileDialog.Directory)

