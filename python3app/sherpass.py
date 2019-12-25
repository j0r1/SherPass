from PyQt5 import QtWidgets, QtGui, QtCore, QtNetwork
from sherpassexception import SherPassExceptionNoConfig, SherPassException
from sherpasstablewidget import SherPassTableWidget
from connectionwrapper import ConnectionWrapper as CW
import ui_sherpass
import logo
import licenses
from logdialog import LogDialog
import configuration
import time
import aescrypt
from passphrasedialog import PassphraseDialog
import lockfile
import gpgdircleanup
import os
import sptempdir
import json
import traceback
import privatekeys
import sharedpass
import sys
from managekeysdialog import ManageKeysDialog
from globaloptionsdialog import GlobalOptionsDialog
import gpgdir
import subprocess
import backgroundprocessdialog
from generatekeydialog import GenerateKeyDialog
from directoriesdialog import DirectoriesDialog
from alreadyrunningdialog import AlreadyRunningDialog
import randomstring
from webserver import WebServer

_shouldShow = [ False ]

class SherPassWindow(QtWidgets.QMainWindow):
    def __init__(self, confDir):
        super(SherPassWindow, self).__init__(None)

        app = QtWidgets.QApplication.instance()
        app.commitDataRequest.connect(self.onCommitDataRequest)

        self.confDir = confDir
        self.lockFileName = "lockfile.lock"
        self.actPortFileName = "portfile.pid"
        self.configFileName = "config_v2.json"
        self.oldConfigFileName = "config.json"

        self.setWindowIcon(logo.getLogo())
        self.sysTrayIcon = QtWidgets.QSystemTrayIcon(logo.getLogo())
        self.sysTrayIcon.hide()
        self.sysTrayIcon.activated.connect(CW(self.toggleShow))

        self.ui = ui_sherpass.Ui_SherPass()
        self.ui.setupUi(self)
        self.ui.passTabs.setSherPass(self)

        self.ui.filterEdit.setFocus()
        self.ui.filterEdit.filterChangedSignal.connect(CW(self.onFilterChanged))
        self.ui.filterEdit.hide()

        self.ui.addEntryButton.clicked.connect(CW(self.ui.passTabs.onAddEntry)) 
        self.ui.changeEntryButton.clicked.connect(CW(self.ui.passTabs.onChangeEntry))
        self.ui.removeEntryButton.clicked.connect(CW(self.ui.passTabs.onRemoveEntry))
        self.ui.sshButton.clicked.connect(CW(self.ui.passTabs.onSSH))

        self.ui.actionChange_to_specific_password.triggered.connect(CW(self.ui.passTabs.onChangeToSpecificPassword))
        self.ui.actionChange_to_random_password.triggered.connect(CW(self.ui.passTabs.onChangeToRandomPassword))

        self.ui.actionQuit.triggered.connect(CW(self.onQuit))
        self.ui.actionVersion.triggered.connect(CW(self.onVersion))
        self.ui.actionWeb_site.triggered.connect(CW(self.onWebSite))
        self.ui.actionTCP_Connection_log.triggered.connect(CW(self.onConnectionLog))
        self.ui.actionSet_master_passphrases.triggered.connect(CW(self.onSetMasterPassphrases))

        self.ui.actionShow_known_keys.triggered.connect(CW(self.ui.passTabs.onShowKnownKeys))
        self.ui.actionRe_load_keys_and_password_entries.triggered.connect(CW(self.ui.passTabs.onReloadKeysAndPasswordEntries))
        self.ui.actionRe_encode_all_known_entries.triggered.connect(CW(self.ui.passTabs.onReEncodeKnownEntries))
        self.ui.actionExport_all_known_entries.triggered.connect(CW(self.ui.passTabs.onExportKnownEntries))

        self.ui.actionAdd_password_collection_tab.triggered.connect(CW(self.ui.passTabs.addEmptyPasswordCollectionTab))
        self.ui.actionRemove_password_collection.triggered.connect(CW(self.ui.passTabs.onRemovePasswordCollectionTab))
        self.ui.actionConfigure_password_collection.triggered.connect(CW(self.ui.passTabs.onConfigurePasswordCollectionTab))

        self.ui.actionGlobal_options.triggered.connect(CW(self.onGlobalOptions))
        self.ui.actionManage_private_keys.triggered.connect(CW(self.onManagePrivateKeys))
        self.ui.actionQuick_start_wizard.triggered.connect(CW(self.onQuickStartWizard))

        self.quitting = True
        self.confirmQuit = False
        self.scheduleAsync(self.onInitialTimeout)

        self.connectionLog = ""
        self.webServer = None

        settings = QtCore.QSettings()
        mainWinGeom = settings.value("mainWindowGeometry")
        mainWinState = settings.value("mainWindowState")
        if mainWinGeom:
            self.restoreGeometry(mainWinGeom)
        if mainWinState:
            self.restoreState(mainWinState)

        self.saveConfigRequested = False
        delayedSaveTimer = QtCore.QTimer(self)
        delayedSaveTimer.setInterval(2000)
        delayedSaveTimer.timeout.connect(CW(self.onCheckSaveConfiguration, False))
        delayedSaveTimer.start()

        checkReloadTimer = QtCore.QTimer(self)
        checkReloadTimer.setInterval(60000) # Base unit is one minute
        checkReloadTimer.timeout.connect(CW(self.onCheckReload, False))
        checkReloadTimer.start()
        self.reloadCount = 1

        checkShowTimer = QtCore.QTimer(self)
        checkShowTimer.setInterval(1000)
        checkShowTimer.timeout.connect(CW(self.onCheckShow, False))
        checkShowTimer.start()

        self.reactivationSockets = [ ]

    def hide(self):
        if self.canHideSafely():
            super(SherPassWindow, self).hide()
            print("hide")
        else:
            super(SherPassWindow, self).showMinimized()
            print("showMinimized")

    def closeEvent(self, e):

        if not self.quitting:
            self.hide()
            e.ignore()
            return
        
        self.quitting = False

        if self.confirmQuit:
            if QtWidgets.QMessageBox.question(self, "Sure?", "Are you sure you want to exit?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
                e.ignore()
                return

        if self.webServer:
            self.webServer.close()
            self.webServer = None

        e.accept()

        settings = QtCore.QSettings()
        settings.setValue("mainWindowGeometry", self.saveGeometry())
        settings.setValue("mainWindowState", self.saveState())

    def onQuit(self, checked):
        self.quitting = True
        self.close()

    def onInitialTimeout(self):

        # Make sure some directories exist
        try:
            tempDirBase = os.path.join(self.confDir, "gpgtempdirs")
            sptempdir.setTempDirBase(tempDirBase)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Fatal error setting temporary directory", "Fatal error setting temporary directory: " + str(e) + "\n\n\nExiting...")
            self.close()
            return

        # Test if we're already running

        try:
            if self.couldBeRunning():
                raise SherPassException("Already running")
        except Exception as e:

            # Try to read the reactivation port file, and open a dummy connection to it
            try:
                pf = self.getActivationPortFilename()
                port = int(open(pf, "rt").read())
                self.openActivationConnection(port)
            except Exception as e:
                print("Unable to reactivate process from port file: {}".format(e))

            dlg = AlreadyRunningDialog(self.getLockFileName())
            dlg.exec_()
            self.close()
            return

        # Don't appear to be running already, start a small server to reactive the
        # process, and write the port to a file
        server = QtNetwork.QTcpServer()
        ret = server.listen(QtNetwork.QHostAddress.LocalHost)
        if not ret:
            QtWidgets.QMessageBox.warning(self, "Can't start reactivation server", "Unable to start TCP server")

        server.newConnection.connect(self.onActivationConnection) # Can't CW() this since we'll also be disconnecting it
        self.reactivationServer = server

        with open(self.getActivationPortFilename(), "wt") as f:
            f.write(str(server.serverPort()))

        # At this point, we'll show the main window as there is no other instance running
        self.toggleShow(None)

        # Test if gpg exists

        class Dummy: pass

        dummy = Dummy()
        dummy.errMsg = None

        def f():
            startTime = time.time()
            try:

                o = subprocess.check_output([gpgdir.gpg, "--version"])
                #o = subprocess.check_output(["sleep", "10"])
                o = o.decode()
                lines = o.splitlines()
                if len(lines) < 1:
                    raise SherPassException("Request for version information does not return any output")
                firstLine = lines[0]
                if not "GnuPG" in firstLine:
                    raise SherPassException("Running GPG executable seems to work, but first line is unexpected:\n" + firstLine)
            except Exception as e:
                dummy.errMsg = str(e)

            endTime = time.time()
            dt = endTime-startTime
            minDt = 1.0
            if dt >= 0.0 and dt < minDt: #  let's wait at least minDt seconds, unity seems to get confused otherwise
                time.sleep(minDt-dt)

        bgDlg = backgroundprocessdialog.BackgroundProcessDialog(self, "Checking GPG...", "Checking if GPG can be used", f)
        bgDlg.exec_()

        if dummy.errMsg:
            QtWidgets.QMessageBox.critical(self, "Fatal error: can't seem to use gpg", "Fatal error: can't seem to use gpg: " + dummy.errMsg + "\n\n\nExiting...")
            self.close()
            return

        # From this point on, the app is useable and we'll show the tray icon
        self.sysTrayIcon.show()

        # If there's anything left in the temporary directory, we'll remove it
        try:
            gpgdircleanup.clean(tempDirBase)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Can't clear the temporary directory", "Error clearing the base temporary directory '{}'\n{}'".format(tempDirBase, str(e)))

        self.quitting = False
        self.confirmQuit = True

        try:
            self.loadConfig()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Can't initialize", "Can't get configuration data: {}\n\nStarting wizard...".format(str(e)))
            self.onQuickStartWizard()
            return

        self.reloadConfiguredPrivateKeys()
        self.restart()

    def scheduleAsync(self, function):
        t = QtCore.QTimer(self)
        t.timeout.connect(CW(function, raiseWindow = False))
        t.setSingleShot(True)
        t.start(0)

    def restart(self):

        testDlg = PassphraseDialog(self)
        if testDlg.exec_() != QtWidgets.QDialog.Accepted:
            QtWidgets.QMessageBox.warning(self, "No private keys", "No useful private key info is present.\n")

        self.clearTabs()
        for pc in configuration.getPassCollections():
            w = self.addTab(pc["PrivPrint"], pc["Name"], pc["PassDir"], pc["PubKeyDir"])
            w.loadEntries()

        self.restartTCPServer()
        self.reloadCount = configuration.getAutoCheckIntervalMinutes()

    def restartTCPServer(self):
        if self.webServer:
            self.webServer.close()
            self.webServer = None

        if configuration.getTcpPort() > 0:
            self.startTCPListener()

    def addTab(self, privateKeyFingerprint, name, passDir, pubKeyDir):
        return self.ui.passTabs.addPasswordCollectionTab(privateKeyFingerprint, name, passDir, pubKeyDir)

    def keyPressEvent(self, evt):
        #super(SherPassWindow, self).keyPressEvent(evt)
        if evt.key() == QtCore.Qt.Key_Tab and evt.modifiers() == QtCore.Qt.ControlModifier:
            num = self.ui.passTabs.count()
            idx = self.ui.passTabs.currentIndex()
            self.ui.passTabs.setCurrentIndex((idx+1)%num)
        else:
            QtWidgets.QApplication.instance().postEvent(self.ui.filterEdit, QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                                    evt.key(), evt.modifiers(), evt.text(), 
                                                                    evt.isAutoRepeat(), evt.count()))
        evt.accept()

    def onFilterChanged(self, txt):
        
        if not txt:
            self.ui.filterEdit.hide()
        else:
            self.ui.filterEdit.show()
            self.ui.filterEdit.setFocus()

        for idx in range(self.ui.passTabs.count()):
            w = self.ui.passTabs.widget(idx)
            w.setFilter(txt)

    def onVersion(self, checked):
        versionString = "Revision: unknown\nDate: unknown\n"

        try:
            import version
            versionString = "Revision: {}\nDate: {}\n".format(version.revisionString, version.dateString)
        except:
            pass

        # Abusing the log dialog for this
        dlg = LogDialog(versionString, self, QtWidgets.QStyle.SP_MessageBoxInformation, "Version", "Info")
        dlg.setLog(licenses.licenses)
        dlg.exec_()

    def onWebSite(self, checked):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://sherpass-lite.appspot.com/about.html"))

    def startTCPListener(self):
        if self.webServer:
            raise SherPassException("Unexpected: self.webServer already exists!")

        port = configuration.getTcpPort()
        accessUrl = configuration.getAccessURL()
        tcpPassPhrase = configuration.getTcpPassPhrase()

        if not (accessUrl and len(accessUrl) >= 12 and tcpPassPhrase and len(tcpPassPhrase) >= 12):
            QtWidgets.QMessageBox.warning(self, "TCP server not available", "The quick access TCP server is requested, but badly configured")
            return

        accessUrl = accessUrl.encode()
        tcpPassPhrase = tcpPassPhrase.encode()

        self.connectionLog = ""
        self.webServer = WebServer(self.getLoadedEntriesAsJSON)
        self.webServer.signalTooManyBadConnections.connect(self.onTooManyBadConnections)
        self.webServer.signalLog.connect(self.appendToConnectionLog)

        try:
            useHTTP = True

            # Try HTTPS first
            certAndKeyFile = os.path.join(self.confDir, "server.pem")
            if os.path.exists(certAndKeyFile):
                self.appendToConnectionLog("Key/Certificate file server.pem detected in configuration directory, trying HTTPS")
                
                certFile = QtCore.QFile(certAndKeyFile)
                keyFile = QtCore.QFile(certAndKeyFile)
                
                if certFile.open(QtCore.QIODevice.ReadOnly) and keyFile.open(QtCore.QIODevice.ReadOnly):
                    sslCert = QtNetwork.QSslCertificate(certFile, QtNetwork.QSsl.Pem)
                    sslKey = QtNetwork.QSslKey(keyFile, QtNetwork.QSsl.Rsa, QtNetwork.QSsl.Pem)

                    if sslCert.isNull() or sslKey.isNull():
                        self.appendToConnectionLog("Key or certificate does not seem valid, reverting to HTTP")
                    else:
                        useHTTP = False
                        self.webServer.startHTTPS(port, accessUrl, tcpPassPhrase, sslCert, sslKey)
                else:
                    self.appendToConnectionLog("Can't read from certificate/key file, reverting to HTTP")

            if useHTTP:
                self.webServer.startHTTP(port, accessUrl, tcpPassPhrase)

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Can't start TCP server", "Unable to start TCP server on port {}:\n{}".format(port, e))
            return

        self.appendToConnectionLog("Web server is listening on port " + str(port))

    def appendToConnectionLog(self, msg):
        self.connectionLog += time.strftime("%Y-%m-%d %H:%M:%S %Z: ") + msg + "\n"
        print(self.connectionLog)
        self.statusBar().showMessage(msg, 10000)

    def getLoadedEntriesAsJSON(self, pretty=False):
    
        data = [ ]
        numTabs = self.ui.passTabs.count()

        if numTabs == 0:
            data = [ ]
        elif numTabs == 1: # old behaviour
            w = self.ui.passTabs.widget(0)
            data = w.getLoadedEntries()
        else:
            tabs = [ ]

            for i in range(self.ui.passTabs.count()):
                w = self.ui.passTabs.widget(i)
                tabs.append({ "name": w.getName(), "entries": w.getLoadedEntries() })

            data = { "collections": tabs, "activecollection": self.ui.passTabs.currentIndex() }

        if pretty:
            ret = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            ret = json.dumps(data)

        return ret.encode()

    def onTooManyBadConnections(self):
        self.appendToConnectionLog("Too many bad connections!")
        QtWidgets.QMessageBox.warning(self, "Stopping TCP server", "Detected too many incoming connections with an invalid location identifier.\nStopping TCP server.")

    def toggleShow(self, status):
        if not self.isVisible():
            self.show()
        
        self.raise_()
        self.activateWindow()

        if self.isMinimized():
            self.showNormal()

    def onConnectionLog(self, checked):
        dlg = LogDialog(None, self)
        dlg.setLog(self.connectionLog)
        dlg.exec_()

    def clearTabs(self):
        while self.ui.passTabs.count():
            w = self.ui.passTabs.widget(0)
            w.clearBeforeRemoval()
            self.ui.passTabs.removeTab(0)

    def onSetMasterPassphrases(self, checked):
        self.restart()

    def loadConfig(self):
        fileName = os.path.join(self.confDir, self.configFileName)

        if not os.path.exists(fileName):
            fileName = os.path.join(self.confDir, self.oldConfigFileName)
            if not os.path.exists(fileName):
                raise SherPassExceptionNoConfig("No config file found")

            try:
                oldConfig = json.loads(open(fileName).read())

                accessUrl = oldConfig.get("AccessUrl")
                tcpPassphrase = oldConfig.get("TcpPassPhrase")
                tcpPort = oldConfig.get("TcpPort")
                sshCommand = oldConfig.get("SshCommand")
                sshEnv = oldConfig.get("SSHPASS")
                
                privateKeyFile = oldConfig["PrivateKey"]
                passDir = oldConfig["PassDir"]
                pubDir = oldConfig["PubKeyDir"]

                keyData = open(privateKeyFile,"rb").read()
                sp = sharedpass.SharedPass(keyData, None, None, False)
                fingerPrint = sp.getOwnFingerprint()

                privateKeyFile = self.tryToSimplify(privateKeyFile)

                privKeyInfo = { 
                        "Name": "Default private key",
                        "PrivateKey": privateKeyFile,
                } 
                passColl = {
                        "Name": "Default password collection",
                        "PrivPrint": fingerPrint,
                        "PassDir": passDir,
                        "PubKeyDir": pubDir
                }

                if QtWidgets.QMessageBox.question(self, "Import old config?", "Can't find config file, but a config file from a previous version can be found. Try to import these settings?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
                    raise SherPassExceptionNoConfig("User cancelled import")
    
                if accessUrl:
                    configuration.setAccessURL(accessUrl)
                if tcpPassphrase:
                    configuration.setTcpPassPhrase(tcpPassphrase)
                if tcpPort:
                    configuration.setTcpPort(tcpPort)
                if sshEnv:
                    configuration.setSshPassEnv(sshEnv)
                if sshCommand:
                    configuration.setSshCommand(sshCommand)

                configuration.setPassCollections([passColl])
                configuration.setPrivateKeys([privKeyInfo])

                self.requestSaveConfiguration(True)
            except Exception as e:
                raise SherPassExceptionNoConfig("No config file found, and unable to import old config: " + str(e))

        else:
            config = json.loads(open(fileName).read())

            # The first part is optional, there are defaults
            configuration.setAccessURL(config.get("AccessUrl"))
            configuration.setTcpPassPhrase(config.get("TcpPassPhrase"))
            configuration.setTcpPort(config.get("TcpPort", 0))
            if "SshPassEnv" in config:
                configuration.setSshPassEnv(config["SshPassEnv"])
            if "SshCommand" in config:
                configuration.setSshCommand(config["SshCommand"])

            configuration.setAutoCheckIntervalMinutes(config.get("AutoCheckInterval", 5))
            configuration.setAutoCheckReload(config.get("AutoCheckReload", False))
            
            # These are absolutely mandatory
            configuration.setPassCollections(config["PassCollections"])
            configuration.setPrivateKeys(config["PrivateKeys"])

    def reloadConfiguredPrivateKeys(self):

        warnings = []

        privatekeys.clear()
        # Load the private keys
        for privKey in configuration.getPrivateKeys():

            keyName = privKey["Name"]
            try:
                fileName = privKey["PrivateKey"]
                
                keyInfo = privatekeys.appendEntry(fileName, keyName)

                if not privKey["PrivateKey"]:
                    raise SherPassException("No file name specified")

                path = os.path.abspath(os.path.join(self.confDir, privKey["PrivateKey"]))
                if not os.path.exists(path):
                    raise SherPassException("Private key file '{}' not found, skipping".format(path))
            
                keyData = open(path, "rb").read()
                keyInfo["data"] = keyData

                sp = sharedpass.SharedPass(keyData, None, None, False)
                fingerPrint = sp.getOwnFingerprint()

                keyInfo["fingerprint"] = fingerPrint
                keyInfo["name"] = keyName

                print("Key '{}' has fingerprint '{}'".format(keyName, fingerPrint))
            except Exception as e:
                warnings.append("Couldn't process private key '{}': {}".format(keyName, str(e)))

        if warnings:
            msg = "\n".join(warnings)
            QtWidgets.QMessageBox.warning(self, "Warnings while reading configuration file", 
                                                "Encountered the following warnings when reading the config file:\n\n" + msg)

    def getLockFileName(self):
        return os.path.join(self.confDir, self.lockFileName)

    def getActivationPortFilename(self):
        return os.path.join(self.confDir, self.actPortFileName)

    def couldBeRunning(self):
        try:
            self.lockFile = lockfile.openLockFile(os.path.join(self.confDir, self.lockFileName))
        except Exception as e:
            print("Couldn't create lock file: ", e)
            return True
        
        return False
        
    def onCheckSaveConfiguration(self):
        if not self.saveConfigRequested:
            return

        try:
            configString = configuration.getFullSettingsString()
            fileName = os.path.join(self.confDir, self.configFileName)
            
            with open(fileName, "wt") as f:
                f.write(configString)

            self.saveConfigRequested = False
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Unable to save config file", 
                                                "Unable to save configuration file:\n{}".format(str(e)))

    def requestSaveConfiguration(self, immediately = False):
        self.saveConfigRequested = True
        if immediately:
            self.scheduleAsync(self.onCheckSaveConfiguration)

    def onGlobalOptions(self, checked):
        dlg = GlobalOptionsDialog(self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        self.requestSaveConfiguration(True)
        self.restartTCPServer()
        self.reloadCount = configuration.getAutoCheckIntervalMinutes()

    def onManagePrivateKeys(self, checked):
        dlg = ManageKeysDialog(self, self.confDir)
        done = False

        while not done:
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                if not dlg.hasChanges():
                    return

                if QtWidgets.QMessageBox.question(self, "Sure?", "Are you sure you want to discard the changes?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                    return
            else:
                done = True

        privKeys = dlg.getPrivateKeys()
        configuration.setPrivateKeys(privKeys)

        self.requestSaveConfiguration(True)
        
        self.reloadConfiguredPrivateKeys()
        self.restart()

    def tryToSimplify(self, path):
        base = os.path.basename(path)
        if os.path.join(self.confDir, base) == path:
            return base

        return path
        
    def onCheckReload(self):
        #print(self.reloadCount)

        if self.reloadCount <= 0: # disables
            #print("Not checking if reload is necessary")
            return

        self.reloadCount -= 1
        if self.reloadCount <= 0:
            #print("Checking if reload is necessary")
            self.reloadCount = configuration.getAutoCheckIntervalMinutes()

            for idx in range(self.ui.passTabs.count()):
                w = self.ui.passTabs.widget(idx)
                w.onCheckReload()

    def onQuickStartWizard(self, checked = True):

        if len(configuration.getPassCollections()) != 0:
            QtWidgets.QMessageBox.warning(self, "Can't run wizard", "There already are password collections configured. Can't start wizard.")
            return

        if len(configuration.getPrivateKeys()) != 0 or len(privatekeys.getKeys()) != 0:
            QtWidgets.QMessageBox.warning(self, "Can't run wizard", "You already seem to have configured a private key. Can't start wizard.\n\nTo use this key, add a password collection tab, and configure it.")
            return

        info = """\
First we need to generate a private key, a corresponding public key will be 
generated as well. Password information will be encrypted using the public
key, but only using the private key it is possible to decrypt the data.

So while - as the name suggests - you do not need to keep the public key
secret, it is very important to keep the private key itself secret. As an
extra safety precaution, the private key itself is protected by a passphrase,
but you should not rely on this alone as a security measure. The private key 
should really be kept private. 

There is no way to recover the private key or the passphrase, so make sure
you don't lose the key or forget the passphrase.

"""
        dlg = GenerateKeyDialog(self, "Specify private key info", info) 
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        
        privateKey = dlg.getKey()
        publicKey = dlg.getPublicKey()
        privateKeyFingerprint = dlg.getFingerPrint()

        info = """\
Now we need to specify some directories.

By default, the private key will be stored in the SherPass configuration
directory. This is probably a good choice, but if you like you can also
save the key somewhere else.

Your public key will be stored in another directory, and if you just want
to use SherPass on your own, it will be the only file in that directory.
To share password entries with other people, the directory must be 
shared and their public keys should be stored there as well.

The password entries will be stored in the last directory. If you want to
share password entries, you should again share this directory with other 
people somehow. By default, new entries will be encrypted with all 
available public keys, but specific keys can be used as well.

"""
        dlg = DirectoriesDialog(self, info)

        while True:
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                if QtWidgets.QMessageBox.question(self, "Sure?", "Are you sure you want to discard the generated key and exit the initial setup?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                    return
            
            else:
                privDir = self.confDir[:] if dlg.useDefaultPrivateKeyDir() else dlg.getPrivateKeyDir()
                pubDir = dlg.getPublicKeyDir()
                passDir = dlg.getPasswordEntryDir()

                try:
                    self.testWritableDirs([privDir, pubDir, passDir], [ "Private key directory", 
                                                                        "Public key directory",
                                                                        "Password entry directory" ])

                    # Check if the pubDir only contains files with key extensions,
                    # otherwise 'sharedpass' will complain later
                    l = [ i for i in os.listdir(pubDir) if not i.startswith(".") ]
                    for i in l:
                        if not sharedpass.isPubKeyFileNameValid(i):
                            raise SherPassException("The public key directory should only contain public key files, but invalid filename '{}' is also present".format(i))

                    # Here we're going to do a stronger check than 'sharedpass' itself does
                    l = [ i for i in os.listdir(passDir) if not i.startswith(".") ]
                    for i in l:
                        if not sharedpass.isPassFileNameValid(i):
                            raise SherPassException("The password entry directory should only contain password entry files, but invalid filename '{}' is also present".format(i))

                    break # Ok exit the loop
                except SherPassException as e:
                    QtWidgets.QMessageBox.warning(self, "Error checking a directory", "Error checking one of the specified directories:\n{}".format(str(e)))

        # Ask for filename prefix and save

        while True:
            keyName, accepted = QtWidgets.QInputDialog.getText(self, "Name the keypair", "Name your private/public key")
            if not accepted:
                if QtWidgets.QMessageBox.question(self, "Sure?", "Are you sure you want to discard the generated key and exit the initial setup?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                    return
            else:            
                try:
                    if os.path.basename(keyName) != keyName:
                        raise SherPassException("The specified key name '{}' refers to another directory".format(keyName))

                    privKeyShort = keyName + ".privkey"
                    privName = os.path.join(privDir, privKeyShort)
                    pubName = os.path.join(pubDir, keyName + ".pubkey")

                    if os.path.exists(privName):
                        raise SherPassException("The name '{}' for the private key seems to be in use already, please change.".format(keyName))
                    if os.path.exists(pubName):
                        raise SherPassException("The name '{}' for the public key seems to be in use already, please change.".format(keyName))

                    break # Ok exit the loop
                
                except SherPassException as e:
                    QtWidgets.QMessageBox.warning(self, "Error saving generated keypair", "Error saving generated keypair:\n{}".format(str(e)))

        with open(privName, "wb") as f:
            f.write(privateKey)

        with open(pubName, "wb") as f:
            f.write(publicKey)
        
        privFileName = privKeyShort if dlg.useDefaultPrivateKeyDir() else privName

        configuration.setPassCollections([ { "Name": "Default password collection",
                                             "PrivPrint": privateKeyFingerprint,
                                             "PassDir": passDir,
                                             "PubKeyDir": pubDir } ])

        configuration.setPrivateKeys([ { "Name": "Default private key",
                                         "PrivateKey": privFileName } ])

        self.requestSaveConfiguration(True)
        self.reloadConfiguredPrivateKeys()
        self.scheduleAsync(self.restart)
    
    def testWritableDirs(self, paths, descriptions):
        pathDesc = zip(paths, descriptions)
        for pd in pathDesc:
            p = pd[0]
            desc = pd[1]
            p = p.strip()
            if not p:
                raise SherPassException("No directory specified for '{}'".format(desc))

            if not os.path.isdir(p):
                raise SherPassException("Path '{}' for '{}' is not an existing directory".format(p,desc))

            testFileName = "." + randomstring.getRandomString(16)
            testPath = os.path.join(p, testFileName)
            try:
                with open(testPath, "wt") as f:
                    f.write("TestData")
                    f.close()
            except Exception as e:
                raise SherPassException("Can't create a test file in '{}' for '{}'".format(p,desc))

            try:
                os.unlink(testPath)
            except Exception as e:
                print("Can't delete test file '{}', ignoring".format(testPath))

    def canHideSafely(self):
        xdgEnv = "XDG_CURRENT_DESKTOP"
        if xdgEnv in os.environ:
            t = os.environ[xdgEnv].lower()
            if "unity" in t or "ubuntu" in t:
                return False

        gdmEnv = "GDMSESSION"
        if gdmEnv in os.environ:
            t = os.environ[gdmEnv]
            if "unity" in t or "ubuntu" in t:
                return False

        return True

    def onCheckShow(self):
        if _shouldShow[0]:
            _shouldShow[0] = False
            self.toggleShow(None)

    def onActivationConnection(self):
        _shouldShow[0] = True

        try:
            conn = self.reactivationServer.nextPendingConnection()
            conn.close()
        except Exception as e:
            print("Unable to close next pending connection: {}".format(e))

    def onActivationSocketConnected(self):
        print("reactivationSockets: {}".format(self.reactivationSockets))

        conn = self.sender()

        newList = [ ]
        for i in self.reactivationSockets:
            if conn is not i:
                newList.append(i)
        self.reactivationSockets = newList

        conn.close()
        print("Closed reactivation connection")
        print("New reactivationSockets: {}".format(self.reactivationSockets))

    def openActivationConnection(self, port):
        sock = QtNetwork.QTcpSocket()
        sock.connected.connect(self.onActivationSocketConnected)
        sock.connectToHost(QtNetwork.QHostAddress.LocalHost, port)

        self.reactivationSockets.append(sock) # make sure the socket isn't destroyed yet


    def onCommitDataRequest(self, manager):
        self.quitting = True
        self.confirmQuit = False
        print("onCommitDataRequest")

