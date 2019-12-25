from PyQt5 import QtCore, QtWidgets
from sshpasswordchanger import SSHPasswordChanger
from logdialog import LogDialog
from connectionwrapper import ConnectionWrapper as CW
import ui_changesshpasswordsdialog
import copy
import time

class OwnPasswordChanger(SSHPasswordChanger):
    def __init__(self, user, host, port, oldPassword, newPassword):
        super(OwnPasswordChanger, self).__init__(user, host, port, oldPassword, newPassword)
        self.forward = None
        self.params = None

    def setCallbackObject(self, o, params):
        self.forward = o
        self.params = params

    def onConnecting(self):
        if self.forward:
            self.forward.onConnecting(self.params)

    def onConnected(self):
        if self.forward:
            self.forward.onConnected(self.params)

    def onChangingPassword(self):
        if self.forward:
            self.forward.onChangingPassword(self.params)

    def onVerifyingOldPasswordDisabled(self):
        if self.forward:
            self.forward.onVerifyingOldPasswordDisabled(self.params)

    def onTestingNewPassword(self):
        if self.forward:
            self.forward.onTestingNewPassword(self.params)

class ChangeThread(QtCore.QThread):
    progressNumber = QtCore.pyqtSignal(int)
    failedSignal = QtCore.pyqtSignal(int, str)
    successSignal = QtCore.pyqtSignal(int)
    connectedSignal = QtCore.pyqtSignal(int)
    hostSignal = QtCore.pyqtSignal(str)
    statusSignal = QtCore.pyqtSignal(str)

    def __init__(self, hostInfo, parent):
        super(ChangeThread, self).__init__(parent)

        self.mutex = QtCore.QMutex()
        self.isCancelled = False
        self.hostInfo = copy.deepcopy(hostInfo)

    def setCancelled(self):
        self.mutex.lock()
        self.isCancelled = True
        self.mutex.unlock()

    def run(self):

        for i in range(len(self.hostInfo)):
            self.progressNumber.emit(i)

            self.mutex.lock()
            cancelled = self.isCancelled
            self.mutex.unlock()

            if cancelled:
                self.exit(-1)
            else:
                hostInfo = self.hostInfo[i]
                spc = OwnPasswordChanger(hostInfo["user"], hostInfo["host"], hostInfo["port"], hostInfo["oldPassword"], hostInfo["newPassword"])
                spc.setCallbackObject(self, i)

                try:
                    spc.start()
                    self.successSignal.emit(i)
                except Exception as e:
                    self.failedSignal.emit(i, str(e))

                # TODO: for testing
                #time.sleep(2)

        self.progressNumber.emit(len(self.hostInfo))

    def onConnecting(self, params):
        host = self.hostInfo[params]["host"]
        user = self.hostInfo[params]["user"]
        port = self.hostInfo[params]["port"]
        self.hostSignal.emit("%s@%s:%d" % (user, host, port))
        self.statusSignal.emit("Connecting")

    def onConnected(self, params):
        self.connectedSignal.emit(params) # params is the index
        self.statusSignal.emit("Connected")

    def onChangingPassword(self, params):
        self.statusSignal.emit("Changing password")

    def onVerifyingOldPasswordDisabled(self, params):
        self.statusSignal.emit("Making sure old password doesn't work anymore")

    def onTestingNewPassword(self, params):
        self.statusSignal.emit("Testing if new password really works")

class ChangeSSHPasswordsDialog(QtWidgets.QDialog):
    def __init__(self, itemsToChange, parent):
        super(ChangeSSHPasswordsDialog, self).__init__(parent)

        self.parent = parent
        self.ui = ui_changesshpasswordsdialog.Ui_ChangeSSHPasswordsDialog()
        self.ui.setupUi(self)

        self.ui.cancelButton.clicked.connect(CW(self.onCancel))

        hostInfo = [ ]
        for i in itemsToChange:
            passInfo = i["passInfo"]
            host = passInfo["host"]
            user = passInfo["login"]
            oldPassword = passInfo["password"]
            newPassword = i["newPassword"]

            port = 22
            idx = host.find(":")
            if idx > 0:
                portStr = host[idx+1:]
                try:
                    port = int(portStr)
                    host = host[:idx]
                except:
                    pass # If the port part is not a number, we'll keep using port 22 and the full hostname

            hostInfo.append( { "host": host, "port": port, "user": user, "oldPassword": oldPassword, "newPassword": newPassword } )
        
        self.threadDone = False
        self.successCount = 0
        self.failedCount = 0
        self.cancelling = False

        self.itemsToChange = itemsToChange
        self.changeThread = ChangeThread(hostInfo, self)
        self.changeThread.finished.connect(CW(self.threadFinished, False))
        self.changeThread.progressNumber.connect(CW(self.progressSlot, False))
        self.changeThread.failedSignal.connect(CW(self.onFailed, False))
        self.changeThread.successSignal.connect(CW(self.onSuccess, False))
        self.changeThread.connectedSignal.connect(CW(self.onStartingHost, False))
        self.changeThread.hostSignal.connect(self.ui.processingEdit.setText)
        self.changeThread.statusSignal.connect(self.ui.statusEdit.setText)
        self.changeThread.start()

    def onCancel(self):
        if not self.threadDone:
            self.changeThread.setCancelled()
            self.cancelling = True
            self.ui.processingEdit.setText("Cancelling...")
            self.ui.statusEdit.setText("Cancelling...")
            return
        
    def closeEvent(self, e):
        if not self.threadDone:
            e.ignore()
            return
        
        e.accept()

        hasLog = False
        for i in self.itemsToChange:
            if len(i["log"]) > 0:
                hasLog = True

        if self.successCount == len(self.itemsToChange) and not hasLog:
            QtWidgets.QMessageBox.information(self, "Done", "Passwords changed successfully for all hosts")
            return

        info = "Entries specified: %d\nSuccess: %d\nFailed: %d" % (len(self.itemsToChange), self.successCount, self.failedCount)

        fullLog = ""
        if self.successCount + self.failedCount < len(self.itemsToChange):
            fullLog += "Not all entries were processed (cancelled?)\n\n"

        for i in self.itemsToChange:
            if len(i["log"]) > 0:
                fullLog += "Entry: %s@%s\n\n" % (i["passInfo"]["login"], i["passInfo"]["host"])
                for line in i["log"]:
                    fullLog += line + "\n"

                fullLog += "\n\n"

        dlg = LogDialog(info, self)
        dlg.setLog(fullLog)
        dlg.exec_()

    # Make sure escape doesn't close the dialog
    def keyPressEvent(self, e):
        e.accept()

    def threadFinished(self):
        self.threadDone = True
        self.close()

    def progressSlot(self, idx):
        self.ui.progressBar.setValue(1.0*idx/len(self.itemsToChange) * 100.0)
        self.ui.progressLabel.setText(str(idx) + "/" + str(len(self.itemsToChange)))

    def onStartingHost(self, idx):

        # To make sure that the password doesn't get lost (in case it's randomly generated),
        # we're going to save it early in the password history and write it to file

        info = self.itemsToChange[idx]
        row = info["row"]
        fileName = info["name"]
        passInfo = info["passInfo"]
        newPassword = info["newPassword"]

        newHistEntry = [ newPassword, time.strftime("%Y-%m-%d %H:%M:%S %Z"), "Attempt" ]

        if "passhist" in passInfo and passInfo["passhist"]:
            passInfo["passhist"].append(newHistEntry)
        else:
            passInfo["passhist"] = [ newHistEntry ]

        try:
            gotWarning = self.parent.addOrUpdateEntry(row, fileName, passInfo)
            if gotWarning:
                info["log"].append("Warning: couldn't use all specified keys for this entry")
        except Exception as e:
            info["log"].append("Error updating entry: could not save new password to file early on: " + str(e))
            self.parent.setEntryMessage(row, "Error")

    def onFailed(self, idx, msg):
        info = self.itemsToChange[idx]
        info["log"].append(msg)
        row = info["row"]
        
        self.parent.setEntryMessage(row, "Error")
        self.failedCount += 1

    def onSuccess(self, idx):

        self.successCount += 1

        info = self.itemsToChange[idx]
        row = info["row"]
        fileName = info["name"]
        passInfo = info["passInfo"]
        newPassword = info["newPassword"]

        lastHistEntry = passInfo["passhist"][-1]
        if len(lastHistEntry) == 3 and lastHistEntry[0] == newPassword and lastHistEntry[2] == "Attempt":
            del lastHistEntry[2]
        else:
            newHistEntry = [ newPassword, time.strftime("%Y-%m-%d %H:%M:%S %Z") ]
            passInfo["passhist"].append(newHistEntry)

        # Make sure the new password is the active password
        passInfo["password"] = newPassword

        try:
            gotWarning = self.parent.addOrUpdateEntry(row, fileName, passInfo, "Password changed")
            if gotWarning:
                info["log"].append("Warning: couldn't use all specified keys for this entry")
        except Exception as e:
            info["log"].append("Error updating entry: could not save new password to file: " + str(e))
            self.parent.setEntryMessage(row, "Error")

