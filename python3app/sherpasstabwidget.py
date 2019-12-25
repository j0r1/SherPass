from PyQt5 import QtCore, QtGui, QtWidgets
import configuration
from connectionwrapper import ConnectionWrapper as CW
from sherpasstablewidget import SherPassTableWidget

class SherpassTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent):
        super(SherpassTabWidget, self).__init__(parent)

        self.sherpass = None

        self.setMovable(True)
        try:
            self.setTabBarAutoHide(True)
        except:
            pass

        self.tabBar().tabMoved.connect(CW(self.onTabOrderChanged))
        self.tabBarDoubleClicked.connect(CW(self.onTabBarDoubleClicked))

    def setSherPass(self, sherpassWidget):
        self.sherpass = sherpassWidget

    def onTabOrderChanged(self, src, dst):
        self.syncTabSettings()

    def onTabBarDoubleClicked(self, idx):
        w = self.widget(idx)
        oldName = w.getName()
        newName, accepted = QtWidgets.QInputDialog.getText(self, "Enter new name", 
                                                                 "New name for '{}'".format(oldName),
                                                                 text = oldName)
        if not accepted:
            return

        w.setName(newName)
        self.syncTabSettings(True)

    def syncTabSettings(self, immediateSync = False):
        passColls = [ ]

        for i in range(self.count()):
            w = self.widget(i)
            coll = { 
                "Name": w.getName(),
                "PrivPrint": w.getPrivateKeyFingerprint(),
                "PassDir": w.getPasswordEntryDir(),
                "PubKeyDir": w.getPublicKeyDir()
            }
            passColls.append(coll)

        configuration.setPassCollections(passColls)
        self.sherpass.requestSaveConfiguration(immediateSync)

    def onTabName(self, n, sender):
        idx = self.indexOf(sender)
        self.setTabText(idx, n)

    def addPasswordCollectionTab(self, privateKeyFingerprint, name, passDir, pubKeyDir):
        w = SherPassTableWidget(self.sherpass)
        w.nameSignal.connect(CW(self.onTabName))
        w.tabConfigChangedSignal.connect(CW(self.syncTabSettings))

        self.addTab(w, "(NoName)")

        w.setPrivateKeyFingerprint(privateKeyFingerprint)
        w.setPasswordEntryDir(passDir)
        w.setPublicKeyDir(pubKeyDir)
        w.setName(name)
        return w

    def addEmptyPasswordCollectionTab(self, checked):
        w = self.addPasswordCollectionTab("", "(no name)", "/set/path/to/password/collection/dir", "/set/path/to/public/key/dir")
        w.loadEntries()
        self.syncTabSettings()
        w.onConfigurePasswordCollectionTab()

    def onRemovePasswordCollectionTab(self, checked):
        w = self.currentWidget()
        if not w:
            return

        if QtWidgets.QMessageBox.question(self, "Sure?", 
                                                "Are you certain you want to remove the tab with name '{}'?\n\n".format(w.getName()) +
                                                "Note that no password entry itself will be removed, only the view.",
                                                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
            return
        
        w.clearBeforeRemoval()
        w.deleteLater()
        idx = self.indexOf(w)
        self.removeTab(idx)

        self.syncTabSettings(True)

    def onAddEntry(self, checked):
        w = self.currentWidget()
        if w:
            w.onAddEntry()

    def onChangeEntry(self, checked):
        w = self.currentWidget()
        if w:
            w.onChangeEntry()

    def onRemoveEntry(self, checked):
        w = self.currentWidget()
        if w: 
            w.onRemoveEntry()

    def onSSH(self, checked):
        w = self.currentWidget()
        if w:
            w.onSSH()

    def onChangeToSpecificPassword(self, checked):
        w = self.currentWidget()
        if w:
            w.onChangeToSpecificPassword()

    def onChangeToRandomPassword(self, checked):
        w = self.currentWidget()
        if w:
            w.onChangeToRandomPassword()

    def onShowKnownKeys(self, checked):
        w = self.currentWidget()
        if w:
            w.onShowKnownKeys()

    def onReloadKeysAndPasswordEntries(self, checked):
        w = self.currentWidget()
        if w:
            w.onReloadKeysAndPasswordEntries()

    def onReloadPasswordEntries(self, checked):
        w = self.currentWidget()
        if w:
            w.onReloadPasswordEntries()

    def onReEncodeKnownEntries(self, checked):
        w = self.currentWidget()
        if w:
            w.onReEncodeKnownEntries()

    def onExportKnownEntries(self, checked):
        w = self.currentWidget()
        if w:
            w.onExportKnownEntries()

    def onConfigurePasswordCollectionTab(self, checked):
        w = self.currentWidget()
        if w:
            w.onConfigurePasswordCollectionTab()
