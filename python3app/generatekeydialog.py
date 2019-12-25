from PyQt5 import QtCore, QtGui, QtWidgets
from connectionwrapper import ConnectionWrapper as CW
import ui_generatekeydialog
import backgroundprocessdialog
import gnupg
import os
import sptempdir
import gpgdir

def createTmpDir():
    gpgTempDir = sptempdir.getTempDir()
    print("Created directory {}".format(gpgTempDir))
    return gpgTempDir

def removeTmpDir(gpgTempDir):
    files = os.listdir(gpgTempDir)
    for f in files:
        fullName = os.path.join(gpgTempDir, f)
        os.unlink(fullName)
        print("Removed {}".format(fullName))

    os.rmdir(gpgTempDir)
    print("Removed {}".format(gpgTempDir))

class GenerateKeyDialog(QtWidgets.QDialog):
    def __init__(self, parent, title = None, infoText = None):
        super(GenerateKeyDialog, self).__init__(parent)

        self.ui = ui_generatekeydialog.Ui_GenerateKeyDialog()
        self.ui.setupUi(self)

        self.ui.generateButton.clicked.connect(CW(self.onGenerate))
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.keysizeCombo.setCurrentIndex(2) # 4096 bits

        if not infoText:
            self.ui.infoTextEdit.hide()
        else:
            self.ui.infoTextEdit.setText(infoText)

        if title:
            self.setWindowTitle(title)

        self.privKey = None
        self.publicKey = None
        self.fingerprint = None

    def onGenerate(self, checked):
        passPhrase = self.ui.passphraseEdit.text()
        if passPhrase != self.ui.passPhraseRepeatEdit.text():
            QtWidgets.QMessageBox.warning(self, "Passphrases don't match", "The specified passphrases are not identical")
            return

        if not passPhrase:
            QtWidgets.QMessageBox.warning(self, "No passphrase", "You must specify a passphrase")
            return

        name = self.ui.nameEdit.text()
        email = self.ui.emailEdit.text()
        if not name or not email:
            QtWidgets.QMessageBox.warning(self, "No name or e-mail address", "You must specify both your name and an e-mail address")
            return

        keySize = int(self.ui.keysizeCombo.currentText())

        gpgTempDir = createTmpDir()

        class Dummy:
            pass

        self.dummy = Dummy()
        self.dummy.keySize = keySize
        self.dummy.name = name
        self.dummy.email = email
        self.dummy.passPhrase = passPhrase
        self.dummy.gpgTempDir = gpgTempDir
        self.dummy.errorMsg = ""
        self.dummy.privKey = None
        self.dummy.publicKey = None
        self.dummy.fingerprint = None

        def f():
            try:
                gpg = gnupg.GPG(gpgbinary=gpgdir.gpg, gnupghome=self.dummy.gpgTempDir, verbose=True)
                input_data = gpg.gen_key_input(key_type="RSA", key_length=self.dummy.keySize, 
                                               name_real=self.dummy.name, name_email=self.dummy.email, 
                                               passphrase=self.dummy.passPhrase)
                gpg.gen_key(input_data)

                privKeys = gpg.list_keys(True)
                ownFingerPrint = privKeys[0]["fingerprint"]

                self.dummy.privKey = str(gpg.export_keys([ownFingerPrint], True)).encode()
                self.dummy.publicKey = str(gpg.export_keys([ownFingerPrint])).encode()
                self.dummy.fingerprint = ownFingerPrint

            except Exception as e:
                self.dummy.errorMsg = "Error trying to generate key: {}".format(str(e))

        bgDlg = backgroundprocessdialog.BackgroundProcessDialog(self, "Generating..", 
                "Generating new private key. If this takes a while, it means\n" +
                "that extra randomness is required. Best to do some work on your\n" +
                "computer in the meantime in that case...", f)

        bgDlg.exec_()

        dummy = self.dummy
        del self.dummy

        if dummy.errorMsg:
            QtWidgets.QMessageBox.warning(self, "Error generating key", dummy.errorMsg)
            return

        removeTmpDir(gpgTempDir)

        self.privKey = dummy.privKey
        self.publicKey = dummy.publicKey
        self.fingerprint = dummy.fingerprint
        self.accept()

    def getKey(self):
        return self.privKey

    def getPublicKey(self):
        return self.publicKey

    def getFingerPrint(self):
        return self.fingerprint
