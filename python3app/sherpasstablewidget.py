from PyQt5 import QtWidgets, QtCore, QtGui
from sherpassexception import SherPassException, SherPassExceptionOwnPubKeyNotFound, SherPassExceptionNoPassphrase
from connectionwrapper import ConnectionWrapper as CW
import sharedpass
import privatekeys
import backgroundprocessdialog
import pprint
import traceback
import popupmenu
from entrydialog import EntryDialog
import configuration
import subprocess
import shlex
import copy
import os
from newpassworddialog import NewPasswordDialog
from changesshpasswordsdialog import ChangeSSHPasswordsDialog
import randomstring
from logdialog import LogDialog
import json
from fingerprintdialog import FingerprintDialog
from tabconfigdialog import TabConfigDialog

class EmptyObject:
    pass

def raiser(f):
    def wrapped(self, *args, **kwargs):
        if not self.mainWin.isVisible():
            self.mainWin.show()

        return f(self, *args, **kwargs)

    return wrapped


def membercallcounter(f):
    def wrapped(self, *args, **kwargs):
        self.memberCallCount += 1
        try:
            return f(self, *args, **kwargs)
        finally:
            self.memberCallCount -= 1

    return wrapped

class SherPassTableWidget(QtWidgets.QTableWidget):
    rightClickSignal = QtCore.pyqtSignal(int, int, int, int)
    nameSignal = QtCore.pyqtSignal(str, "QWidget")
    tabConfigChangedSignal = QtCore.pyqtSignal(bool)

    def __init__(self, parent):
        super(SherPassTableWidget, self).__init__(parent)

        self.mainWin = parent
        self.memberCallCount = 0

        self.popupMenu = popupmenu.PopupMenu(None)

        self.name = "(untitled)"
        self.passDir = None
        self.pubkeyDir = None
        self.privKeyFingerprint = None
        self.sharedPass = None

        self.delayedScroll = [ ]

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.cellDoubleClicked.connect(CW(self.onEntryDoubleClicked))
        self.rightClickSignal.connect(CW(self.onEntryRightClicked))
        
        self.cellActivated.connect(CW(self.onSelectRow))
        #self.cellChanged.connect(CW(self.onSelectRow))
        #self.cellClicked.connect(CW(self.onSelectRow))
        #self.cellEntered.connect(CW(self.onSelectRow))
        self.cellPressed.connect(CW(self.onSelectRow))

    @membercallcounter
    def setName(self, n):
        self.name = n
        self.nameSignal.emit(n, self)

    @membercallcounter
    def setPasswordEntryDir(self, d):
        self.passDir = d

    @membercallcounter
    def setPublicKeyDir(self, d):
        self.pubkeyDir = d

    @membercallcounter
    def setPrivateKeyFingerprint(self, fp):
        self.privKeyFingerprint = fp

    @membercallcounter
    def onSelectRow(self, row, col):
        self.selectRow(row)

    @membercallcounter
    def getName(self):
        return copy.copy(self.name)

    @membercallcounter
    def getPasswordEntryDir(self):
        return copy.copy(self.passDir);

    @membercallcounter
    def getPublicKeyDir(self):
        return copy.copy(self.pubkeyDir)

    @membercallcounter
    def getPrivateKeyFingerprint(self):
        return copy.copy(self.privKeyFingerprint)

    #def mousePressEvent(self, evt):
    #    super(SherPassTableWidget, self).mouseReleaseEvent(evt)
    #    pass

    @membercallcounter
    def mouseReleaseEvent(self, evt):
        super(SherPassTableWidget, self).mouseReleaseEvent(evt)

        x = self.columnAt(evt.x())
        y = self.rowAt(evt.y())

        if evt.button() == QtCore.Qt.RightButton:
            if x >= 0 and y >= 0:
                self.rightClickSignal.emit(y, x, evt.globalX(), evt.globalY())

        self.selectRow(y)

    @membercallcounter
    def hasFilter(self, filt, obj):
        if not filt:
            return False
        filt = filt.lower()

        if obj is None:
            return False

        if type(obj) == dict:
            for value in obj.values():
                if self.hasFilter(filt, value):
                    return True
        
        elif type(obj) == list:
            for value in obj:
                if self.hasFilter(filt, value):
                    return True

        else:
            if filt in str(obj).lower():
                return True

        return False

    @membercallcounter
    def setFilter(self, filt):

        if not self.arePasswordEntriesShown(): # Not initialized
            return

        rows = self.rowCount()
        for r in range(rows):
            item = self.item(r, 0)

            if filt:
                gotMatch = False
                entryData = item.entryData[1]
                for (field,value) in entryData.items():
                    if field in [ "login", "host", "description", "extra" ]:
                        if self.hasFilter(filt, value):
                            gotMatch = True
                            break

                self.setRowHidden(r, not gotMatch)
            else:
                self.setRowHidden(r, False)

        self.resizeColumnsToContents()
                        
    @membercallcounter
    def clear(self):
        while self.rowCount():
            self.removeRow(0)

        while self.columnCount():
            self.removeColumn(0)

    @membercallcounter
    def setErrorMessage(self, msg, doubleClickHandler = None):
        self.clear()
        self.insertColumn(0)

        self.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem("Error message"))

        self.insertRow(0)

        item = QtWidgets.QTableWidgetItem(msg)
        item.doubleClickHandler = doubleClickHandler

        self.setItem(0, 0, item)
        self.resizeColumnsToContents()

    @membercallcounter
    def loadEntries(self):

        noPubKey = False
        sp = None

        try:
            key, passphrase = privatekeys.getKeyAndPassphrase(self.privKeyFingerprint) 

            self.sharedPass = None
            
            dummy = EmptyObject()
            dummy.errorMsg = None
            dummy.noPubKey = False

            def bgProc():
                try:
                    self.sharedPass = sharedpass.SharedPass(key, self.pubkeyDir, self.passDir, False, passphrase)
                    self.sharedPass.syncPublicKeys()
                    self.sharedPass.syncPassInfo()
                except SherPassExceptionOwnPubKeyNotFound as e:
                    dummy.errorMsg = str(e)
                    dummy.noPubKey = True
                except Exception as e:
                    # TODO: disable this
                    traceback.print_exc()
                    dummy.errorMsg = str(e)

            bgDlg = backgroundprocessdialog.BackgroundProcessDialog(self, "Decoding...", "Decoding password entries for '{}'".format(self.name), bgProc)
            bgDlg.exec_()

            noPubKey = dummy.noPubKey
            msg = dummy.errorMsg

            if noPubKey:
                sp = self.sharedPass # We'll need this later

            if msg is not None:
                raise SherPassException("Unable to decrypt password entries: " + msg)

            self.redisplayLoadedPasswords()

        except SherPassExceptionNoPassphrase as e:
            self.setErrorMessage("Invalid passphrase. Double click to set passphrases and restart.", self.mainWin.restart)
            self.sharedPass = None

        except SherPassException as e:
            self.setErrorMessage(str(e))
            self.sharedPass = None

        # If the error is caused by the fact that our own public key is not in
        # the directory of public keys, suggest a fix
        if noPubKey:
            if QtWidgets.QMessageBox.question(self, "Public key not found", 
                                                    "The public key for password collection '{}' is not found in directory '{}'.\n\nDo you wish to save it there?".format(self.name, self.pubkeyDir), 
                                                    QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                pubkey = sp.exportPublicKey()
                self.savePublicKey(pubkey)

    @membercallcounter
    def savePublicKey(self, pubkey):
        try:
            name, ok = QtWidgets.QInputDialog.getText(self, "Enter public key name",
                                                            "Please specify the base filename for the public key")
            if ok:
                if not name.endswith(".pubkey"):
                    name += ".pubkey"

            # Make sure we didn't specify another directory
            if os.path.basename(name) != name:
                raise SherPassException("The specified filename '{}' refers to another directory".format(name))

            fullName = os.path.join(self.pubkeyDir, name)
            if os.path.exists(fullName):
                raise SherPassException("The file '{}' already exists in directory '{}'. Refusing to overwrite.".format(name, self.pubkeyDir))

            with open(fullName, "wb") as f:
                f.write(pubkey)

            self.scheduleAsync(self.loadEntries)
            
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Can't save public key", "Unable to save public key:\n" + str(e))

    @membercallcounter
    def redisplayLoadedPasswords(self):

        if not self.sharedPass:
            raise SherPassException("No passwords could be decrypted for '{}'".format(self.name))

        passes = self.sharedPass.listPasswords()
        if passes is None:
            raise SherPassException("No passwords could be listed for '{}'".format(self.name))

        passes.sort(key=lambda a: a[1]["description"].lower())

        modelIdx = self.indexAt(QtCore.QPoint(1,1))
        print("ModelIdx = ", modelIdx)

        self.clear()
        for i in range(5):
            self.insertColumn(i)

        self.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem("Type"))
        self.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem("Description"))
        self.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem("Login"))
        self.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem("Host"))
        self.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem("Status"))

        for entry in passes:
            self.appendEntryToTable(entry)

        if modelIdx.isValid():
            row = modelIdx.row()
        else:
            row = 0

        print("Scrolling to row", row)
        self.delayedScroll.append(row)
        #self.delayedScroll.append(0)

        self.scheduleAsync(self.delayedScrollTimeout)

    @membercallcounter
    def scheduleAsync(self, function, timeout = 0):
        t = QtCore.QTimer(self)
        t.timeout.connect(CW(function, raiseWindow = False))
        t.setSingleShot(True)
        t.start(timeout)

    @membercallcounter
    def delayedScrollTimeout(self):

        if not self.delayedScroll:
            return

        row = self.delayedScroll[0]
        self.delayedScroll = self.delayedScroll[1:]

        it = self.item(row, 0)
        if it:
            self.scrollToItem(it, QtWidgets.QAbstractItemView.PositionAtTop)

        if self.delayedScroll:
            self.scheduleAsync(self.delayedScrollTimeout)

    @membercallcounter
    def setEntryMessage(self, row, msg):
        if msg:
            self.setItem(row, 4, QtWidgets.QTableWidgetItem(msg))
        else:
            self.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
        self.resizeColumnsToContents()
        
    @membercallcounter
    def appendEntryToTable(self, newEntry):
        row = self.rowCount()
        self.insertRow(row)

        self.setRowEntry(row, newEntry)

    @membercallcounter
    def setRowEntry(self, row, newEntry, message = None):
        # We're going to abuse the first column to attach some extra info

        typeEntry = QtWidgets.QTableWidgetItem(newEntry[1]["type"])
        typeEntry.entryData = newEntry
        typeEntry.doubleClickHandler = None

        self.setItem(row, 0, typeEntry)
        self.setItem(row, 1, QtWidgets.QTableWidgetItem(newEntry[1]["description"]))
        self.setItem(row, 2, QtWidgets.QTableWidgetItem(newEntry[1]["login"]))
        self.setItem(row, 3, QtWidgets.QTableWidgetItem(newEntry[1]["host"]))
        self.setEntryMessage(row, message)

    @membercallcounter
    def keyPressEvent(self, evt):
        super(SherPassTableWidget, self).keyPressEvent(evt)
        #if not evt.isAccepted():
        QtWidgets.QApplication.instance().postEvent(self.mainWin, QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                                    evt.key(), evt.modifiers(), evt.text(), 
                                                                    evt.isAutoRepeat(), evt.count()))
        evt.accept()

    @membercallcounter
    def onEntryDoubleClicked(self, row, col):

        # Check if we've got a special handler
        item = self.item(row, 0)
        if item.doubleClickHandler:
            self.scheduleAsync(item.doubleClickHandler)
            return

        if not self.arePasswordEntriesShown():
            return

        if not self.sharedPass:
            self.warnNoConfig()
            return

        self.selectRow(row)

        dlg = EntryDialog(True, self.sharedPass.listPublicKeys(), self)
        dlg.setPassInfo(item.entryData[1])
        dlg.exec_()

    @membercallcounter
    def onEntryRightClicked(self, row, col, globalX, globalY):

        if not self.arePasswordEntriesShown():
            return

        item = self.item(row, 0)
        self.popupMenu.process(item.entryData[0], item.entryData[1], globalX, globalY)

    @membercallcounter
    def warnNoConfig(self):
        QtWidgets.QMessageBox.warning(self, "No valid config settings processed", "No valid config settings processed for password collection '{}'".format(self.name))

    @membercallcounter
    def filterFingerPrints(self, entryData):
        gotWarning = False
        knownFingerprints = set([ p for (p,n) in self.sharedPass.listPublicKeys() ])
        ownPrint = self.sharedPass.getOwnFingerprint()

        fingerPrints = entryData["fingerprints"]
        filteredPrints = None # 'None' means all fingerprints

        if fingerPrints is not None:
            filteredPrints = set()
            filteredPrints.add(ownPrint) # Always make sure we can decode it ourselves

            for p in fingerPrints:
                if p in knownFingerprints:
                    filteredPrints.add(p)
                else:
                    gotWarning = True

            if not ownPrint in entryData["fingerprints"]:
                entryData["fingerprints"].append(ownPrint)

            tmp = set(entryData["fingerprints"])
            entryData["fingerprints"] = [ p for p in tmp ] # Make sure the entry does not contain any duplicates

        return (gotWarning, filteredPrints) 

    @membercallcounter
    def addOrUpdateEntry(self, row, name, passInfo, message = None):
        (gotWarning, filteredPrints) = self.filterFingerPrints(passInfo)
        if row < 0 or not name:
            newEntry = self.sharedPass.addPassword(passInfo, filteredPrints)
            self.appendEntryToTable(newEntry)
            self.redisplayLoadedPasswords()
        else:
            newEntry = self.sharedPass.updatePassword(name, passInfo, filteredPrints)
            self.setRowEntry(row, newEntry)

        self.setEntryMessage(row, message)
        return gotWarning 

    @membercallcounter
    def onAddEntry(self):

        if not self.arePasswordEntriesShown():
            return

        if not self.sharedPass:
            self.warnNoConfig()
            return

        dlg = EntryDialog(False, self.sharedPass.listPublicKeys(), self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        passInfo = dlg.getPassInfo()

        gotWarning = self.addOrUpdateEntry(-1, None, passInfo)
        if gotWarning:
            QtWidgets.QMessageBox.warning(self, "Bad fingerprints", "Not all specified fingerprints were found in the keys, only used the known ones")

    @membercallcounter
    def getMultipleSelectedRows(self):
        items = self.selectedItems()

        selRows = set()
        for i in items:
            selRows.add(i.row())

        rows = [ row for row in selRows ]
        rows.sort()
        return rows

    @membercallcounter
    def getSelectedRow(self):
        selRows = self.getMultipleSelectedRows()

        if len(selRows) == 0:
            QtWidgets.QMessageBox.warning(self, "No items selected", "No items selected")
            return -1

        if len(selRows) != 1:
            QtWidgets.QMessageBox.warning(self, "Multiple items selected", "Can't work with multiple selected items")
            return -1

        return selRows[0]

    @membercallcounter
    def onChangeEntry(self):
    
        if not self.arePasswordEntriesShown():
            return

        if not self.sharedPass:
            self.warnNoConfig()
            return

        row = self.getSelectedRow()
        if row < 0:
            return

        item = self.item(row, 0)
        dlg = EntryDialog(False, self.sharedPass.listPublicKeys(), self)
        dlg.setPassInfo(item.entryData[1])

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        passInfo = dlg.getPassInfo()

        gotWarning = self.addOrUpdateEntry(row, item.entryData[0], passInfo)
        if gotWarning:
            QtWidgets.QMessageBox.warning(self, "Bad fingerprints", "Not all specified fingerprints were found in the keys, only used the known ones")

    @membercallcounter
    def onRemoveEntry(self):

        if not self.arePasswordEntriesShown():
            return

        if not self.sharedPass:
            self.warnNoConfig()
            return

        row = self.getSelectedRow()
        if row < 0:
            return
        
        item = self.item(row, 0)
        entryID = item.entryData[0]
        entryDesc = item.entryData[1]["description"]

        warning = "Are you sure you want to remove row %d, for '%s'" % (row+1, entryDesc)
        if QtWidgets.QMessageBox.question(self, "Sure?", warning, QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        self.sharedPass.removePassword(entryID) 
        self.removeRow(row)

    @membercallcounter
    def onSSH(self):

        if not self.arePasswordEntriesShown():
            return
        
        if not self.sharedPass:
            self.warnNoConfig()
            return

        row = self.getSelectedRow()
        if row < 0:
            return

        item = self.item(row, 0)
        entry = item.entryData[1]

        if entry["type"] != "SSH":
            QtWidgets.QMessageBox.warning(self, "Wrong type", "Selected entry does not have the type 'SSH'")
            return

        host = entry["host"]
        user = entry["login"]
        password = entry["password"]

        port = 22
        idx = host.find(":")
        if idx > 0:
            portStr = host[idx+1:]
            try:
                port = int(portStr)
                host = host[:idx]
            except:
                pass # If the port part is not a number, we'll keep using port 22 and the full hostname

        sshCommand = configuration.getSshCommand()
        if not sshCommand:
            QtWidgets.QMessageBox.warning(self, "Bad config", "The SSH command to execute was not configured")
            return

        sshCommand = shlex.split(sshCommand)
        substCommand = [ ]
        for i in sshCommand:
            e = i.replace("%h", host)
            e = e.replace("%u", user)
            e = e.replace("%p", password)
            e = e.replace("%P", str(port))
            substCommand.append(e)

        env = copy.deepcopy(os.environ)

        sshPassEnv = configuration.getSshPassEnv()
        if sshPassEnv:
            env[sshPassEnv] = password

        try:
            pid = subprocess.Popen(substCommand, env=env)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error launching SSH command", "Can't start SSH:\n" + str(e))

    @membercallcounter
    def commonChangePasswordChecks(self):
        if not self.arePasswordEntriesShown():
            return None

        if not self.sharedPass:
            self.warnNoConfig()
            return None
        
        allRows = self.getMultipleSelectedRows()
        rows = [ ]
        for r in allRows:
            item = self.item(r, 0)
            entry = item.entryData[1]
            if entry["type"] == "SSH":
                rows.append(r)
        
        if len(rows) == 0:
            QtWidgets.QMessageBox.warning(self, "No SSH entries selected", "Unable to change password: no SSH entries were selected")
            return None

        return rows

    @membercallcounter
    def onChangeToSpecificPassword(self):
        rows = self.commonChangePasswordChecks()
        if not rows:
            return

        dlg = NewPasswordDialog(self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        newPassword = dlg.getPassword()
        itemsToChange = [ ]
        for r in rows:
            item = self.item(r,0)
            name = item.entryData[0]
            passInfo = item.entryData[1]
            itemsToChange.append( { "row": r, "name": name, "passInfo": passInfo, "newPassword": newPassword, "log": [ ] } )

        self.changeSSHPasswords(itemsToChange)

    @membercallcounter
    def onChangeToRandomPassword(self):
        rows = self.commonChangePasswordChecks()
        if not rows:
            return

        itemsToChange = [ ]
        log = ""
        for r in rows:
            item = self.item(r,0)
            name = item.entryData[0]
            passInfo = item.entryData[1]
            newPassword = randomstring.getRandomString(16)
            itemsToChange.append( { "row": r, "name": name, "passInfo": passInfo, "newPassword": newPassword, "log": [ ] } )
            log += "%s@%s -> '%s'\n" % (passInfo["login"], passInfo["host"], newPassword)

        dlg = LogDialog("Going to try to install the following random passwords\n" + 
                        "for the following hosts. Please temporarily copy/paste them\n" +
                        "somewhere, in case something goes wrong and the password gets\n" +
                        "installed but not saved into the password entry!", self)
        dlg.setLog(log)
        dlg.exec_()

        self.changeSSHPasswords(itemsToChange)

    @membercallcounter
    def changeSSHPasswords(self, itemsAndPasswords):
        if QtWidgets.QMessageBox.question(self, "Sure?", "Are you really sure you want to set new SSH passwords on all selected hosts?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        self.clearStatusColumn()
        dlg = ChangeSSHPasswordsDialog(itemsAndPasswords, self)
        dlg.exec_()

    @membercallcounter
    def clearStatusColumn(self):
        rows = self.rowCount()
        for r in range(rows):
            self.setItem(r, 4, QtWidgets.QTableWidgetItem(""))

    @membercallcounter
    def getLoadedEntries(self):
        if not self.arePasswordEntriesShown():
            return [ ]

        try:
            return [ self.item(r, 0).entryData[1] for r in range(self.rowCount()) ]
        except Exception as e:
            print("Can't getLoadedEntries:", e)
            
        return [ ]

    @membercallcounter
    def getLoadedEntriesAsJSON(self):
        data = self.getLoadedEntries()
        body = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        return body.encode()

    @membercallcounter
    def clearBeforeRemoval(self):
        del self.mainWin
        del self.popupMenu
        del self.name
        del self.passDir
        del self.pubkeyDir
        del self.privKeyFingerprint
        del self.sharedPass 
        del self.delayedScroll

    @membercallcounter
    def onShowKnownKeys(self):
        if not self.sharedPass:
            self.warnNoConfig()
            return

        dlg = FingerprintDialog(self.sharedPass.listPublicKeys(), True, self)
        dlg.exec_()

    @membercallcounter
    @raiser
    def onReloadKeysAndPasswordEntries(self):
        if not self.sharedPass:
            self.loadEntries()
            return

        try:
            self.sharedPass.syncPublicKeys()
        except SherPassException as e:
            QtWidgets.QMessageBox.warning(self, "Unable to sync public keys", "Can't sync public keys for '{}':\n{}".format(self.name,str(e)))
            self.setErrorMessage(str(e))
            self.sharedPass = None
            return

        dummy = EmptyObject()
        dummy.errorMsg = None
        def bgProc():
            try:
                self.sharedPass.syncPassInfo()
            except Exception as e:
                # TODO: disable this
                traceback.print_exc()
                dummy.errorMsg = str(e)

        bgDlg = backgroundprocessdialog.BackgroundProcessDialog(self, "Decoding...", "Decoding password entries for '{}'".format(self.name), bgProc)
        bgDlg.exec_()

        msg = dummy.errorMsg

        if msg:
            QtWidgets.QMessageBox.warning(self, "Unable to sync passwords", "Can't sync password entries for '{}':\n{}".format(self.name,msg))
            self.setErrorMessage(msg)
            self.sharedPass = None
            return

        # Everything ok, show the entries
        self.redisplayLoadedPasswords()

    @membercallcounter
    def arePasswordEntriesShown(self):
        return self.columnCount() > 1

    @membercallcounter
    def onReEncodeKnownEntries(self):

        if not self.arePasswordEntriesShown():
            return

        if not self.sharedPass:
            self.warnNoConfig()
            return

        warning = "Are you sure you want to re-encode all entries for '{}'?".format(self.name)
        if QtWidgets.QMessageBox.question(self, "Sure?", warning, QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        warning = "Not all fingerprints found for:"
        gotWarning = False

        # TODO: attach things for background process to a dummy object, not 'self'

        self.idDataPrint = [ ]
        rows = self.rowCount()
        for r in range(rows):
            item = self.item(r, 0)
            entryID = item.entryData[0]
            entryData = item.entryData[1]

            (gotSubWarning, filteredPrints) = self.filterFingerPrints(entryData)

            if gotSubWarning:
                warning += "\n * " + entryData["description"]
                gotWarning = True

            # Going to store it in a list for now, so we can do the encoding
            # in the background
            self.idDataPrint.append((entryID, entryData, filteredPrints))

        self.bgError = None

        def backgroundFunction():
            try:
                for entryID, entryData, filteredPrints in self.idDataPrint:
                    self.sharedPass.updatePassword(entryID, entryData, filteredPrints)
            except Exception as e:
                self.bgError = "Error while encoding entries: " + str(e)

        bgDlg = backgroundprocessdialog.BackgroundProcessDialog(self, "Encoding...", "Re-encoding password entries for '{}'".format(self.name), backgroundFunction)
        bgDlg.exec_()
         
        del self.idDataPrint
        if not gotWarning:
            QtWidgets.QMessageBox.information(self, "Done", "All entries have been re-encoded with specified keys")
        else:
            QtWidgets.QMessageBox.warning(self, "Can't encode all entries", warning)

        if self.bgError:
            QtWidgets.QMessageBox.warning(self, "Error while encoding", self.bgError)
        del self.bgError

    @membercallcounter
    def onExportKnownEntries(self):

        if not self.arePasswordEntriesShown():
            return

        if not self.sharedPass:
            self.warnNoConfig()
            return

        data = self.getLoadedEntriesAsJSON()
        
        fileName, filt = QtWidgets.QFileDialog.getSaveFileName(self, "Choose file to save passwords to", filter="JSON Text Files (*.json)")
        if not fileName:
            return

        try:
            with open(fileName, "wt") as f:
                f.write(data.decode())
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Can't write to specified file", "Error writing to '%s'\n%s" % (fileName, str(e)))

    @membercallcounter
    def onConfigurePasswordCollectionTab(self):
        dlg = TabConfigDialog(self, self.name)
        dlg.setPublicKeyDirectory(self.pubkeyDir)
        dlg.setPasswordEntriesDirectory(self.passDir)
        dlg.setPrivateKeyFingerprint(self.privKeyFingerprint)

        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        if QtWidgets.QMessageBox.question(self, "Sure?", 
                                                "Are you certain you want to change the settings for the tab with name '{}'?".format(self.name),
                                                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return

        name = dlg.getTabName()
        self.setName(name)

        self.pubkeyDir = dlg.getPublicKeyDirectory()
        self.passDir = dlg.getPasswordEntriesDirectory()
        self.privKeyFingerprint  = dlg.getPrivateKeyFingerprint()

        self.tabConfigChangedSignal.emit(True)
        self.loadEntries()

    @membercallcounter
    def onCheckReload(self):

        # print(self.memberCallCount)

        # Make sure that nothing else is going on
        if self.memberCallCount != 1: # means we're not the only one
            # Rescheduling in 30 seconds
            self.scheduleAsync(self.onCheckReload, 30000)
            return

        if not self.sharedPass:
            return
        if not self.arePasswordEntriesShown():
            return

        if self.sharedPass.hasDifferentKeys() or self.sharedPass.hasDifferentPasswordEntries():
            if configuration.getAutoCheckReload(): # Really reload
                self.scheduleAsync(self.onReloadKeysAndPasswordEntries)
            else: # Just show a message telling the user to reload
                self.setErrorMessage("Public keys or password entries have changed. Double click to reload",
                                     self.onReloadKeysAndPasswordEntries)


