import os

os.environ["DYLD_LIBRARY_PATH"] = "/Applications/SherPass.app/Contents/lib/"
os.environ["DYLD_FRAMEWORK_PATH"] = "/Applications/SherPass.app/Contents/frameworks4/"
os.environ["PATH"] = os.environ["PATH"] + ":/Applications/SherPass.app/Contents/bin"

import main
main.main()
