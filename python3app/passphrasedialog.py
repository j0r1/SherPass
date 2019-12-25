from PyQt5 import QtCore, QtWidgets
from sherpassexception import *
from connectionwrapper import ConnectionWrapper as CW
import ui_passphrasedialog
import logo
import privatekeys
import randomstring
import sharedpass
from backgroundprocessdialog import BackgroundProcessDialog
import sys

class PassphraseDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super(PassphraseDialog, self).__init__(parent)

        self.ui = ui_passphrasedialog.Ui_PassphraseDialog()
        self.ui.setupUi(self)

        self.ui.okButton.clicked.connect(CW(self.onOk))
        self.ui.sherpassIcon.setPixmap(logo.getPixmap())

        keys = privatekeys.getKeys(False)
    
        # The placeholders are just so Qt Designer has something to show,
        # we'll just hide them
        self.ui.placeholderLabel.hide()
        self.ui.placeholderEdit.hide()

        self.passInfo = { }
        self.passWidgets = { }
        self.passWidgetList = [ ]
        for k in keys:
            fp = k["fingerprint"]
            if not fp:
                continue
            
            if not fp in self.passInfo:
                self.passInfo[fp] = [ ]
            
            self.passInfo[fp].append(k)

        row = 1
        for fp,keyList in self.passInfo.items():

            names = ""
            for idx,k in enumerate(keyList):
                n = k["name"] or "(unnamed key)"
                if idx > 0:
                    names += " / "
                names += n

            lab = QtWidgets.QLabel(names, self)
            edt = QtWidgets.QLineEdit(self)
            edt.setEchoMode(QtWidgets.QLineEdit.Password)
            edt.setMinimumWidth(150)
            edt.returnPressed.connect(CW(self.onReturnPressed))
            
            for k in keyList:
                pf = k["passphrase"]
                if pf:
                    break

            if pf:
                edt.setText(pf)

            self.ui.passphraseGrid.addWidget(lab, row, 0, 1, 1)
            self.ui.passphraseGrid.addWidget(edt, row, 1, 1, 1)

            self.passWidgets[edt] = fp
            self.passWidgetList.append(edt)
            row += 1

        for fp,keyList in self.passInfo.items():
            if len(keyList) > 1:
                QtWidgets.QMessageBox.warning(self, "Identical key fingerprints", "There are private keys with the same fingerprint present.\n")
                break

        if len(self.passWidgetList) == 0: # No useful keys present
            # Show dialog from determining return value
            #QtWidgets.QMessageBox.warning(self, "No private keys", "No useful private key info is present.\n")
            
            t = QtCore.QTimer(self)
            t.setInterval(0)
            t.setSingleShot(True)
            t.timeout.connect(self.reject)
            t.start()

            self.hide()
        else:
            self.passWidgetList[0].setFocus()

    def closeEvent(self, e):
        e.ignore()

    def onOk(self, checked = False):
        for edt in self.passWidgetList:
            passPhrase = edt.text()
            fp = self.passWidgets[edt]
            for k in self.passInfo[fp]:
                k["passphrase"] = passPhrase

        self.errorString = ""
        self.allOk = True

        # Check passphrases
        def checkPassphrases():
            try:
                keys = privatekeys.getKeys(False)
                passPhraseTrials = [ ]

                # First disable all passphrases, so that only the correct ones will be set
                for k in keys:
                    if k["fingerprint"] and k["data"]:
                        passPhraseTrials.append((k, k["passphrase"]))
                        k["passphrase"] = None

                for k,passphrase in passPhraseTrials:

                    sp = sharedpass.SharedPass(k["data"], None, None, False, passphrase)
                    plainText = randomstring.getRandomString(32).encode()
                    encText = sp.encrypt(plainText, None)
                    decText = None
                    try:
                        decText = sp.decrypt(encText)
                    except SherPassException as e:
                        print("Ignoring exception: ", e, file=sys.stderr)

                    if decText != plainText:
                        self.allOk = False
                    else:
                        k["passphrase"] = passphrase

            except Exception as e:
                self.errorString = str(e)

        checkDlg = BackgroundProcessDialog(self, "Verifying passphrases", "Verifying passphrases...", checkPassphrases)
        checkDlg.exec_()

        if self.errorString:
            QtWidgets.QMessageBox.warning(self, "Error during verification", "Unexpected error during passphrase verification:\n" + self.errorString)
        else:
            if not self.allOk:
                QtWidgets.QMessageBox.warning(self, "Bad passphrase(s)", "Not all entered passphrases are correct")

        self.accept()

    # Make sure escape doesn't close the dialog
    def keyPressEvent(self, e):
        e.accept()

    def onReturnPressed(self):
        edt = self.sender()
        try:
            idx = self.passWidgetList.index(edt)
        except ValueError:
            # Not found in list
            return

        if idx == len(self.passWidgetList)-1:
            self.onOk()
        else:
            nextEdt = self.passWidgetList[idx+1]
            nextEdt.setFocus()

