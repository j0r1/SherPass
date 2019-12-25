from PyQt5 import QtWidgets, QtCore, QtGui
from connectionwrapper import ConnectionWrapper as CW

class PopupMenu(QtWidgets.QMenu):
    def __init__(self, parent):
        super(PopupMenu, self).__init__(parent)
        
        self.passInfo = None

        desc = QtWidgets.QAction("Copy description", self)
        host = QtWidgets.QAction("Copy hostname", self)
        login = QtWidgets.QAction("Copy login", self)
        password = QtWidgets.QAction("Copy password", self)
        info = QtWidgets.QAction("Copy info field", self)
        fileName = QtWidgets.QAction("Copy file name", self)

        self.addAction(desc)
        self.addAction(host)
        self.addAction(login)
        self.addAction(password)
        self.addAction(info)
        self.addAction(fileName)

        desc.triggered.connect(CW(self.onCopyDescription, False))
        host.triggered.connect(CW(self.onCopyHostname, False))
        login.triggered.connect(CW(self.onCopyLogin, False))
        password.triggered.connect(CW(self.onCopyPassword, False))
        info.triggered.connect(CW(self.onCopyInfo, False))
        fileName.triggered.connect(CW(self.onCopyFileName, False))

    def process(self, fileName, passInfo, globalX, globalY):
        self.fileName = fileName
        self.passInfo = passInfo
        self.exec_(QtCore.QPoint(globalX, globalY))

    def onCopyDescription(self, checked):
        self.copy("description")

    def onCopyHostname(self, checked):
        self.copy("host")

    def onCopyLogin(self, checked):
        self.copy("login")

    def onCopyPassword(self, checked):
        self.copy("password")

    def onCopyInfo(self, checked):
        self.copy("extra")

    def onCopyFileName(self, checked):
        clip = QtWidgets.QApplication.clipboard()
        clip.setText(self.fileName)

    def copy(self, fieldName):
        clip = QtWidgets.QApplication.clipboard()
        clip.setText(self.passInfo[fieldName])


