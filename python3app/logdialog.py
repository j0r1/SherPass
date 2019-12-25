from PyQt5 import QtWidgets
import ui_logdialog

class LogDialog(QtWidgets.QDialog):
    def __init__(self, msg, parent, msgType = QtWidgets.QStyle.SP_MessageBoxWarning, title = "Log", label = "Warning"):
        super(LogDialog, self).__init__(parent)

        self.ui = ui_logdialog.Ui_LogDialog()
        self.ui.setupUi(self)

        self.ui.closeButton.clicked.connect(self.reject)
        
        iconId = msgType

        style = QtWidgets.QApplication.style()
        icon = style.standardIcon(iconId).pixmap(64, 64)

        self.ui.iconLabel.setMinimumWidth(icon.width())
        self.ui.iconLabel.setMaximumWidth(icon.width())
        self.ui.iconLabel.setMinimumHeight(icon.height())
        self.ui.iconLabel.setMaximumHeight(icon.height())
        self.ui.iconLabel.setPixmap(icon)

        if label:
            self.ui.warningGroupBox.setTitle(label)

        if not msg:
            self.ui.warningGroupBox.hide()
        else:
            self.ui.infoLabel.setText(msg)

        self.setWindowTitle(title)

    def setLog(self, log):
        self.ui.logEdit.setPlainText(log)

