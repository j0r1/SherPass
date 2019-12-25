#!/usr/bin/env python3

import subprocessmod
import gpgdir
import lockfile
import sptempdir
import os
import sys
import json
import sharedpass
import randomstring
import gpgdircleanup
from sherpassexception import SherPassException
from PyQt5 import QtWidgets, QtCore
import sherpass
import privatekeys
import configuration

import getpass
import pprint

def getDefaultConfigDir():
    homeDir = os.path.expanduser("~")
    configDir = os.path.join(homeDir,".sherpass")
    return configDir

def main():
    app = QtWidgets.QApplication(sys.argv)
    if len(sys.argv) > 2:
        print("The only allowed (optional) parameter is a base configuration directory")
        sys.exit(-1)

    QtCore.QCoreApplication.setOrganizationDomain("sherpass-lite.appspot.com")
    QtCore.QCoreApplication.setOrganizationName("SherPass")
    QtCore.QCoreApplication.setApplicationName("SherPass")

    confDir = getDefaultConfigDir() if len(sys.argv) == 1 else sys.argv[1]
    confDir = os.path.abspath(confDir)

    sherPassWidget = sherpass.SherPassWindow(confDir)
    #sherPassWidget.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

