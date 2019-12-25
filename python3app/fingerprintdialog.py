#!/usr/bin/env python

from PyQt5 import QtCore, QtWidgets
from connectionwrapper import ConnectionWrapper as CW
import ui_fingerprintdialog
import copy

class FingerprintDialog(QtWidgets.QDialog):
    def __init__(self, knownKeys, readOnly, parent):
        super(FingerprintDialog, self).__init__(parent)

        self.ui = ui_fingerprintdialog.Ui_FingerprintDialog()
        self.ui.setupUi(self)

        self.ui.closeButton.clicked.connect(self.reject)

        row = 0
        for e in knownKeys:
            self.ui.fingerprintTable.insertRow(row)
            self.ui.fingerprintTable.setItem(row, 0, QtWidgets.QTableWidgetItem(e[0]))
            self.ui.fingerprintTable.setItem(row, 1, QtWidgets.QTableWidgetItem(e[1]))
            row += 1

        self.ui.fingerprintTable.resizeColumnsToContents()
        self.ui.fingerprintTable.setColumnWidth(0, 100)

        if readOnly:
            self.ui.addButton.hide()
        else:
            self.ui.addButton.clicked.connect(CW(self.onAdd))

        self.selectedFingerprints = [ ]

    def getSelectedRows(self):
        items = self.ui.fingerprintTable.selectedItems()

        rows = set()
        for item in items:
            row = item.row()
            rows.add(row)

        return [ r for r in rows ]

    def onAdd(self, checked):
        rows = self.getSelectedRows()
        self.selectedFingerprints = [ ]
        
        for r in rows:
            fp = self.ui.fingerprintTable.item(r, 0).text()
            name = self.ui.fingerprintTable.item(r, 1).text()

            self.selectedFingerprints.append( (fp, name) )

        self.accept()

    def getSelectedFingerprints(self):
        return copy.deepcopy(self.selectedFingerprints)

