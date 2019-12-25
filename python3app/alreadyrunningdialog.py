from PyQt5 import QtWidgets, QtCore
from connectionwrapper import ConnectionWrapper as CW

class AlreadyRunningDialog(QtWidgets.QMessageBox):
    def __init__(self, lockFileName):

        super(AlreadyRunningDialog, self).__init__(QtWidgets.QMessageBox.Critical,
                "Already running", 
                "An instance of SherPass using this config directory already seems to be running.\nDelete the file '{}' if not".format(lockFileName),
                flags = QtCore.Qt.Dialog | QtCore.Qt.MSWindowsFixedSizeDialogHint | QtCore.Qt.WindowStaysOnTopHint ) 

        self.show()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(CW(self.onTimeout))
        self.timer.setInterval(1000)
        self.timer.start()

    def onTimeout(self):
        self.raise_()
        self.activateWindow()

