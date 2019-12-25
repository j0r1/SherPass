import sys
import os

print("Looking for gpg binary", file=sys.stderr)
gpg = "gpg"

if hasattr(sys, "_MEIPASS"):

    print("Seems to be a PyInstaller created package", file=sys.stderr)
    testExe = os.path.join(sys._MEIPASS, "gpg.exe")

    if os.path.exists(testExe):
        gpg = testExe

else:
    print("Not a PyInstaller package", file=sys.stderr)

print("using gpg:", gpg, file=sys.stderr)

