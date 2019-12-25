from PyQt5 import QtWidgets, QtCore, QtGui
import ui_tabconfigdialog
from connectionwrapper import ConnectionWrapper as CW
import privatekeys
from selectkeydialog import SelectKeyDialog

class TabConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent, tabName):
        super(TabConfigDialog, self).__init__(parent)

        self.ui = ui_tabconfigdialog.Ui_TabConfigDialog()
        self.ui.setupUi(self)

        self.ui.tabNameEdit.setText(tabName)

        self.ui.privKeyChangeButton.clicked.connect(CW(self.onChangePrivateKey))
        self.ui.pubkeyBrowseButton.clicked.connect(CW(self.onBrowsePublicKeyDir))
        self.ui.passBrowseButton.clicked.connect(CW(self.onBrowsePassDir))
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.saveButton.clicked.connect(self.accept)

    def setPublicKeyDirectory(self, n):
        if not n:
            n = ""
        self.ui.pubkeyDirEdit.setText(n)

    def setPasswordEntriesDirectory(self, n):
        if not n:
            n = ""
        self.ui.passDirEdit.setText(n or "")

    def setPrivateKeyFingerprint(self, fp):
        keyNames = [ k["name"] for k in privatekeys.getKeysForFingerprint(fp) ]
        self.fingerprint = fp if keyNames else None

        names = " / ".join(keyNames)
        self.ui.privKeyNameEdit.setText(names)
        self.ui.privKeyFingerprintEdit.setText(self.fingerprint or "")

    def onChangePrivateKey(self, checked):
        keys = [ (k["name"], k["fingerprint"]) for k in privatekeys.getKeys() if k["fingerprint"] and k["data"] ]

        dlg = SelectKeyDialog(self)
        dlg.setAvailableKeys(keys)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        fp = dlg.getSelectedFingerprint()
        self.setPrivateKeyFingerprint(fp)

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

    def getTabName(self):
        return self.ui.tabNameEdit.text()

    def getPublicKeyDirectory(self):
        return self.ui.pubkeyDirEdit.text()

    def getPasswordEntriesDirectory(self):
        return self.ui.passDirEdit.text()

    def getPrivateKeyFingerprint(self):
        return self.fingerprint
