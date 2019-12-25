# This modules provides a function 'ConnectionWrapper' which 
# can be used to catch exceptions in slots as well as to
# activate the window when the signal fires

from PyQt5 import QtWidgets
import traceback
import sys

class _HelperClass:
    def __init__(self, f, o, s):
        self.f = f
        self.o = o
        self.s = s

    def handler(self, *args):
        try:
            if self.s:
                try:
                    self.o.show()
                except:
                    pass

                try:
                    self.o.showNormal()
                except:
                    pass

                try:
                    self.o.raise_()
                except:
                    pass

                try:
                    self.o.activateWindow()
                except:
                    pass

            self.f(*args)
        except Exception as e:
            s = traceback.format_exc()
            print(s, file=sys.stderr)
            QtWidgets.QMessageBox.warning(self.o, "Unexpected exception " + str(type(e)), "Unexpected exception:\n" + str(e) + "\n\n" + s)

def ConnectionWrapper(realFunction, raiseWindow = True):

    owner = realFunction.__self__
    x = _HelperClass(realFunction, owner, raiseWindow)

    try:
        owner.justSomeNameToAvoidGarbageCollection.append(x)
    except:
        owner.justSomeNameToAvoidGarbageCollection = [ x ]

    return x.handler

