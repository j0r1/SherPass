import sys
import os

sys.stderr = open(os.devnull,"w")
sys.stdout = open(os.devnull,"w")

import main
main.main()
