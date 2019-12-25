import sys
import os

def _removeFileOrDir(path):
    if os.path.isdir(path):
        
        # First remove the contents, should all be regular files

        files = os.listdir(path)
        for fileName in files: # We're not expecting any further directories, and don't want to go recursive
            name = os.path.join(path, fileName)
            print("Removing", name, file=sys.stderr)
            os.unlink(name)

        # Then remove the directory itself
        print("Removing", path, file=sys.stderr)
        os.rmdir(path)
    else:
        print("Removing", path, file=sys.stderr)
        os.unlink(path)

def clean(path):

    basePath = os.path.abspath(path)
    files = os.listdir(basePath)
    for fileName in files:
        name = os.path.join(basePath, fileName)
        _removeFileOrDir(name) # This is not recursive but should work for both a file and a directory (that doesn't contain any more directories)



