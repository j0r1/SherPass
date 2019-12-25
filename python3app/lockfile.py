import portalocker
import sys
import os

def openLockFile(fileName, writePID = True):
    f = open(fileName, "wt")
    portalocker.lock(f, portalocker.LOCK_EX|portalocker.LOCK_NB)
    if writePID:
        f.write(str(os.getpid()))
    f.flush()
    return f

if __name__ == "__main__":
    n = sys.argv[1]
    try:
        f = openLockFile(n)
        print("Locked", n)
        print("Press enter to exit...")
        input()
    except portalocker.LockException as e:
        print("Unable to lock file '{}': {}".format(n,str(e)))
