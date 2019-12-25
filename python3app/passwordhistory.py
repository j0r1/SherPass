#!/usr/bin/env python

from PyQt5 import QtCore, QtWidgets
import ui_passwordhistory

class PasswordHistory(QtWidgets.QDialog):
    def __init__(self, hist, parent):
        super(PasswordHistory, self).__init__(parent)

        self.ui = ui_passwordhistory.Ui_PasswordHistory()
        self.ui.setupUi(self)

        self.ui.closeButton.clicked.connect(self.reject)

        row = 0
        for h in hist:
            self.ui.histTable.insertRow(row)
            self.ui.histTable.setItem(row, 0, QtWidgets.QTableWidgetItem(h[1]))
            self.ui.histTable.setItem(row, 1, QtWidgets.QTableWidgetItem(h[0]))

        self.ui.histTable.resizeColumnsToContents()

