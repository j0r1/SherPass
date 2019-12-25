from sherpassexception import SherPassException
import randomstring
import sys
import os

class _TempDirBase:
    def __init__(self):
        self.value = None

_tempDirBase = _TempDirBase()

def setTempDirBase(s):
    if not os.path.exists(s):
        os.makedirs(s, 0o0700)

    absPath = os.path.abspath(s)
    if not os.path.isdir(absPath):
        raise SherPassException("Path '{}' exists, but is not a directory and therefore cannot be used as a base for temporary directories".format(absPath))

    _tempDirBase.value = absPath
    print("Set base dir for temporary directories to", absPath, file=sys.stderr)

def getTempDir():
    if not _tempDirBase.value:
        raise SherPassException("No temporary directory base has been set")

    maxAttempts = 10
    for i in range(maxAttempts):
        subDir = randomstring.getRandomString(16)
        fullDir = os.path.join(_tempDirBase.value, subDir)
        if not os.path.exists(fullDir):
            break
    else:
        raise SherPassException("Couldn't create a unique subdirectory of '{0}' in {1} attempts".format(_tempDirBase.value, maxAttempts))

    os.makedirs(fullDir, 0o0700)
    return fullDir

if __name__ == "__main__":
    setTempDirBase(sys.argv[1])
    getTempDir()
