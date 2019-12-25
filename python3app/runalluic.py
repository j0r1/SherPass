#!/usr/bin/env python3

import subprocess
import glob

uicFiles = glob.glob("*.ui")
for fileName in uicFiles:
    with open("ui_" + fileName[:-3] + ".py", "wb") as f:
        subprocess.check_call( [ "pyuic5", fileName ], stdout=f)

