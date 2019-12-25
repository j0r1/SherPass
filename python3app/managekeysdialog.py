from PyQt5 import QtWidgets, QtCore, QtGui
from connectionwrapper import ConnectionWrapper as CW
import ui_managekeysdialog
import configuration
import os
from generatekeydialog import GenerateKeyDialog
from keysavedialog import KeySaveDialog

class ManageKeysDialog(QtWidgets.QDialog):
    def __init__(self, parent, confDir):
        super(ManageKeysDialog, self).__init__(parent)

        self.confDir = confDir

        self.ui = ui_managekeysdialog.Ui_ManageKeysDialog()
        self.ui.setupUi(self)

        self.ui.keyTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ui.keyTable.cellDoubleClicked.connect(CW(self.onEntryDoubleClicked))
        self.ui.addEntryButton.clicked.connect(CW(self.onAddEntry))
        self.ui.removeEntryButton.clicked.connect(CW(self.onRemoveEntry))
        self.ui.generateButton.clicked.connect(CW(self.onGenerate))

        keys = configuration.getPrivateKeys()

        for k in keys:
            row = self.ui.keyTable.rowCount()
            self.ui.keyTable.insertRow(row)
            self.setKeyInfo(row, k["Name"], k["PrivateKey"])

        self.changes = False

    def getPrivateKeys(self):
        keys = [ ]
        rows = self.ui.keyTable.rowCount()
        for row in range(rows):
            name = self.ui.keyTable.item(row, 0).text()
            pathItem = self.ui.keyTable.item(row, 1)
            if name or pathItem.path is not None:
                keys.append({ "Name": name, "PrivateKey": pathItem.path })

        return keys

    def onAddEntry(self, checked):
        row = self.ui.keyTable.rowCount()
        self.ui.keyTable.insertRow(row)
        self.setKeyInfo(row, "", None)

        self.changes = True

    def onRemoveEntry(self, checked):
        items = self.ui.keyTable.selectedItems()

        selRows = set()
        for i in items:
            selRows.add(i.row())

        rows = [ row for row in selRows ]
        rows.sort()

        if len(rows) == 0:
            return

        if len(rows) != 1:
            QtWidgets.QMessageBox.warning(self, "Multiple items selected", "Can't work with multiple selected entries")
            return

        row = rows[0]
        self.ui.keyTable.removeRow(row)

        self.changes = True

    def setKeyInfo(self, row, name, path):
        self.ui.keyTable.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
        
        if path is not None:
            if os.path.dirname(path):
                shortName = os.path.join("...", os.path.basename(path))
            else:
                shortName = path
        else:
            shortName = "(not set)"

        pathItem = QtWidgets.QTableWidgetItem(shortName)
        pathItem.path = path
        self.ui.keyTable.setItem(row, 1, pathItem)

        if path is not None:
            msg = "Can't read"
            fullPath = None
            try:
                fullPath = os.path.join(self.confDir, path)
                open(fullPath,"rb").read()
                msg = ""
            except Exception as e:
                # TODO set error as tooltip?
                print("Can't open file {}: {}".format(str(fullPath), str(e)))

            self.ui.keyTable.setItem(row, 2, QtWidgets.QTableWidgetItem(msg))

        self.ui.keyTable.resizeColumnsToContents()

        self.changes = True

    def onEntryDoubleClicked(self, row, col):
        item = self.ui.keyTable.item(row, col)
        if col == 0:
            oldName = item.text()
            newName, accepted = QtWidgets.QInputDialog.getText(self, "Enter new name", "New name: ", text = oldName)
            if not accepted:
                return

            item.setText(newName)
            self.changes = True

        elif col == 1:

            dlg = QtWidgets.QFileDialog()
            if item.path is not None:
                fullPath = os.path.join(self.confDir, item.path)
                print("fullPath", fullPath, "dirname", os.path.dirname(fullPath))
                dlg.setDirectory(os.path.dirname(fullPath))

            dlg.setNameFilters([ "Private key files (*.privkey)" ])
            if dlg.exec_():
                f = dlg.selectedFiles()
                print(f)
                if f:
                    name = self.ui.keyTable.item(row, 0).text()
                    self.setKeyInfo(row, name, f[0])

                    self.changes = True

    def onGenerate(self, checked):
        dlg = GenerateKeyDialog(self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        
        privKeyData = dlg.getKey()
        
        done = False
        dlg = KeySaveDialog(self)

        while not done:
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return

            fileName = dlg.getFileName()
            if not fileName.endswith(".privkey"):
                fileName += ".privkey"

            fullPath = os.path.join(self.confDir, fileName)
            if os.path.exists(fullPath):
                QtWidgets.QMessageBox.warning(self, "File exists", "Specified file already exists, please specify another")
                continue

            try:
                with open(fullPath, "wb") as f:
                    f.write(privKeyData)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Can't write to file", "Can't write to file '{}'.\nError: {}".format(fullPath, str(e)))
                continue

            done = True

        row = self.ui.keyTable.rowCount()
        self.ui.keyTable.insertRow(row)
        self.setKeyInfo(row, "", fileName)
        
        self.changes = True

    def hasChanges(self):
        return self.changes
