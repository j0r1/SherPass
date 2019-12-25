from PyQt5 import QtCore, QtWidgets
from passwordhistory import PasswordHistory
from fingerprintdialog import FingerprintDialog
from connectionwrapper import ConnectionWrapper as CW
import ui_entrydialog
import time
import copy
import randomstring
import pprint

class EntryDialog(QtWidgets.QDialog):
    def __init__(self, readOnly, knownKeys, parent):
        super(EntryDialog, self).__init__(parent)

        self.readOnly = readOnly

        self.ui = ui_entrydialog.Ui_EntryDialog()
        self.ui.setupUi(self)

        self.ui.saveButton.clicked.connect(CW(self.onSave))
        self.ui.cancelButton.clicked.connect(CW(self.onCancel))
        
        self.ui.passEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ui.showCheckBox.clicked.connect(CW(self.onPasswordShowClicked))
        self.ui.generateButton.clicked.connect(CW(self.onGeneratePassword))
        self.ui.passHistButton.clicked.connect(CW(self.onPasswordHistory))
        self.ui.allKeysCheckbox.clicked.connect(CW(self.onToggleAllFingerprints))
        self.ui.addKeyButton.clicked.connect(CW(self.onAddFingerPrints))
        self.ui.removeKeyButton.clicked.connect(CW(self.onRemoveFingerPrints))
        self.ui.copyButton.clicked.connect(CW(self.onCopyToClipboard))

        self.knownKeys = knownKeys

        if readOnly:
            self.ui.saveButton.hide()
            self.ui.cancelButton.setText("Close")
            self.ui.passEdit.setReadOnly(True)
            self.ui.hostEdit.setReadOnly(True)
            self.ui.loginEdit.setReadOnly(True)
            self.ui.extraInfoEdit.setReadOnly(True)
            self.ui.descEdit.setReadOnly(True)

            self.ui.typeCombo.setDisabled(True)
            self.ui.generateButton.setDisabled(True)
            self.setWindowTitle("View password entry")

            self.ui.allKeysCheckbox.setDisabled(True)
            self.ui.addKeyButton.setDisabled(True)
            self.ui.removeKeyButton.setDisabled(True)

        self.passInfo = { "description": "", "host": "", "type": "SSH", "login": "", "password": "", "passhist": [ ], "extra": "", "fingerprints": None }

        passInfo = copy.deepcopy(self.passInfo)
        self.setPassInfo(passInfo)

    def onGeneratePassword(self, checked):
        if self.readOnly:
            return

        rndStr = randomstring.getRandomString(16)
        self.ui.passEdit.setText(rndStr)
        QtWidgets.QMessageBox.information(self, "New password", "New random password was generated")

    def onPasswordShowClicked(self, checked):
        mode = QtWidgets.QLineEdit.Normal if self.ui.showCheckBox.checkState() == QtCore.Qt.Checked else QtWidgets.QLineEdit.Password
        self.ui.passEdit.setEchoMode(mode)

    def isKnown(self, fingerprint):
        for (fp, name) in self.knownKeys:
            if fp == fingerprint:
                return (fp, name)

        return None

    def setPassInfo(self, passInfo):
        self.passInfo = copy.deepcopy(passInfo)
        
        self.ui.hostEdit.setText(passInfo["host"])
        t = [ "SSH", "HTTPS", "HTTP", "Other" ].index(passInfo["type"])
        if t >= 0:
            self.ui.typeCombo.setCurrentIndex(t)
        else:
            QtWidgets.QMessageBox.warning(self, "Invalid type", "Unsupported type '%s' in password entry" % passInfo["type"])

        self.ui.loginEdit.setText(passInfo["login"])
        self.ui.passEdit.setText(passInfo["password"])
        self.ui.extraInfoEdit.setPlainText(passInfo["extra"])
        self.ui.descEdit.setText(passInfo["description"])

        # Clear the table
        rows = self.ui.fingerprintTable.rowCount()
        for r in range(rows):
            self.ui.fingerprintTable.removeRow(0)
    
        if passInfo["fingerprints"] is None: # Means all fingerprints
            self.ui.allKeysCheckbox.setCheckState(QtCore.Qt.Checked)
            self.ui.addKeyButton.hide()
            self.ui.removeKeyButton.hide()
            self.ui.fingerprintTable.hide()
        else:
            self.ui.allKeysCheckbox.setCheckState(QtCore.Qt.Unchecked)
            self.ui.addKeyButton.show()
            self.ui.removeKeyButton.show()
            self.ui.fingerprintTable.show()

            for fp in passInfo["fingerprints"]:
                row = self.ui.fingerprintTable.rowCount()
                self.ui.fingerprintTable.insertRow(row)
                self.ui.fingerprintTable.setItem(row, 0, QtWidgets.QTableWidgetItem(fp))

                known = self.isKnown(fp)
                if known:
                    self.ui.fingerprintTable.setItem(row, 1, QtWidgets.QTableWidgetItem("yes"))
                    self.ui.fingerprintTable.setItem(row, 2, QtWidgets.QTableWidgetItem(known[1]))
                else:
                    self.ui.fingerprintTable.setItem(row, 1, QtWidgets.QTableWidgetItem("no"))
                    self.ui.fingerprintTable.setItem(row, 2, QtWidgets.QTableWidgetItem("(unknown)"))

        self.ui.fingerprintTable.resizeColumnsToContents()
        self.ui.fingerprintTable.setColumnWidth(0, 100)


    def getPassInfo(self):
        if self.readOnly:
            return None
        return copy.deepcopy(self.passInfo)

    def onSave(self, checked):
        if self.readOnly:
            return

        if QtWidgets.QMessageBox.question(self, "Sure?", "Are you sure you want to save this entry?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        descStr = self.ui.descEdit.text()
        hostStr = self.ui.hostEdit.text()
        typeStr = self.ui.typeCombo.currentText()
        loginStr = self.ui.loginEdit.text()
        passStr = self.ui.passEdit.text()
        extraStr = self.ui.extraInfoEdit.toPlainText()

        if passStr != self.passInfo["password"]:
            self.passInfo["passhist"].append( [ passStr, time.strftime("%Y-%m-%d %H:%M:%S %Z") ] )

        self.passInfo["description"] = descStr
        self.passInfo["host"] = hostStr
        self.passInfo["type"] = typeStr
        self.passInfo["login"] = loginStr
        self.passInfo["password"] = passStr
        self.passInfo["extra"] = extraStr

        if self.ui.allKeysCheckbox.checkState() == QtCore.Qt.Checked:
            self.passInfo["fingerprints"] = None
        else:
            rows = self.ui.fingerprintTable.rowCount()
            fpList = [ ]
            for row in range(rows):
                item = self.ui.fingerprintTable.item(row, 0)
                fpList.append(item.text())

            self.passInfo["fingerprints"] = fpList

        self.accept()

    def onCancel(self, checked):
        self.reject()

    def onPasswordHistory(self, checked):
        dlg = PasswordHistory(self.passInfo["passhist"], self)
        dlg.exec_()

    def onToggleAllFingerprints(self, checked):
        if self.ui.allKeysCheckbox.checkState() == QtCore.Qt.Checked:
            if QtWidgets.QMessageBox.question(self, "Sure?", "This will clear all current entries from the table, are you sure you want this?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
                self.ui.allKeysCheckbox.setCheckState(QtCore.Qt.Unchecked)
                return

            # Clear the table
            rows = self.ui.fingerprintTable.rowCount()
            for r in range(rows):
                self.ui.fingerprintTable.removeRow(0)

            self.ui.addKeyButton.hide()
            self.ui.removeKeyButton.hide()
            self.ui.fingerprintTable.hide()
        else:
            self.ui.addKeyButton.show()
            self.ui.removeKeyButton.show()
            self.ui.fingerprintTable.show()

    def getSelectedRows(self):
        items = self.ui.fingerprintTable.selectedItems()

        rows = set()
        for item in items:
            row = item.row()
            rows.add(row)

        return [ r for r in rows ]

        
    def onRemoveFingerPrints(self, checked):
        sel = self.getSelectedRows()
        if not sel:
            QtWidgets.QMessageBox.warning(self, "No selection", "No fingerprints were selected for deletion")
            return
        
        if QtWidgets.QMessageBox.question(self, "Sure?", "This will remove %d row(s), are you sure?" % len(sel), QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        sel.sort()
        sel.reverse() # We'll delete the highest indices first, so the numbering stays valid

        for r in sel:
            self.ui.fingerprintTable.removeRow(r)

    def onAddFingerPrints(self, checked):
        dlg = FingerprintDialog(self.knownKeys, False, self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        currentPrints = set()
        rows = self.ui.fingerprintTable.rowCount()
        for r in range(rows):
            currentPrints.add(self.ui.fingerprintTable.item(r, 0).text())

        selectedPrints = dlg.getSelectedFingerprints()
        for p in selectedPrints:
            if not p[0] in currentPrints:
                row = self.ui.fingerprintTable.rowCount()
                self.ui.fingerprintTable.insertRow(row)
                self.ui.fingerprintTable.setItem(row, 0, QtWidgets.QTableWidgetItem(p[0]))
                self.ui.fingerprintTable.setItem(row, 1, QtWidgets.QTableWidgetItem("yes"))
                self.ui.fingerprintTable.setItem(row, 2, QtWidgets.QTableWidgetItem(p[1]))

        self.ui.fingerprintTable.resizeColumnsToContents()
        self.ui.fingerprintTable.setColumnWidth(0, 100)

    def onCopyToClipboard(self, checked):
        clip = QtWidgets.QApplication.clipboard()
        clip.setText(self.ui.passEdit.text())

