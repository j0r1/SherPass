import platform
import os
import copy
import json

def _findExeInPath(fileName):

    path = os.environ.get("PATH")
    if not path:
        return False

    isWin = True if platform.system() == "Windows" else False

    paths = path.split(os.pathsep)
    for p in paths:
        fullFileName = os.path.join(p, fileName)
        if os.path.isfile(fullFileName):
            if isWin:
                return True
            if os.access(fullFileName, os.X_OK):
                return True
    
    return False

_settings = { 
    "Version": 2,
    "AccessUrl": None,
	"TcpPassPhrase": None, 
	"TcpPort": 0, 
	"SshPassEnv": "SSHPASS", 
	"SshCommand": None,
    "PrivateKeys": [ ],
    "PassCollections": [ ],
    "AutoCheckInterval": 5,
    "AutoCheckReload": False
}

# Set some defaults for various platforms
if platform.system() == "Windows":
    _settings["SshCommand"] = "putty.exe -pw %p -l %u -P %P %h"
elif platform.system() == "Darwin":
    _settings["SshCommand"] = "qterminal -e sshpass -e ssh -p %P %u@%h"
else: # Assume Linux
    if _findExeInPath("gnome-terminal"):
        _settings["SshCommand"] = 'gnome-terminal -t "%u@%h" -e "sshpass -e ssh -p %P %u@%h"'
    else:
        _settings["SshCommand"] = "xterm -T \"%u@%h\" -e \"sshpass -e ssh -p %P %u@%h ; sleep 5\""

def _checkStrOrNone(u):
    if not (u is None or type(u) == str):
        raise TypeError("Expecting a string or None")
    return u

def _checkInt(v, minVal, maxVal):
    if not (type(v) == int):
        raise TypeError("Expecting an integer")
    if not (minVal <= v <= maxVal):
        raise ValueError("Value must lie between {} and {} but is {}".format(minVal, maxVal, v))
    return v

def _checkPassCollection(c):
    name = _checkStrOrNone(c["Name"]) or ""
    fp = _checkStrOrNone(c["PrivPrint"]) or ""
    passDir = _checkStrOrNone(c["PassDir"]) or ""
    pubDir = _checkStrOrNone(c["PubKeyDir"]) or ""

    return { "Name": name, "PrivPrint": fp, "PassDir": passDir, "PubKeyDir": pubDir }

def _checkBoolean(b):
    if not (type(b) == bool):
        raise TypeError("Expecting a boolean value")
    return b

def _checkPrivateKeyInfo(k):
    name = _checkStrOrNone(k["Name"]) or ""
    privKey = _checkStrOrNone(k["PrivateKey"]) or ""
    return { "PrivateKey": privKey, "Name": name }

def setAccessURL(u):
    _settings["AccessUrl"] = _checkStrOrNone(u)

def getAccessURL():
    return copy.copy(_settings["AccessUrl"])

def setTcpPassPhrase(p):
    _settings["TcpPassPhrase"] = _checkStrOrNone(p)

def getTcpPassPhrase():
    return copy.copy(_settings["TcpPassPhrase"])

def setTcpPort(n):
    _settings["TcpPort"] = _checkInt(n, 0, 65535)

def getTcpPort():
    return copy.copy(_settings["TcpPort"])

def setSshPassEnv(e):
    _settings["SshPassEnv"] = _checkStrOrNone(e)

def getSshPassEnv():
    return copy.copy(_settings["SshPassEnv"])

def setSshCommand(c):
    _settings["SshCommand"] = _checkStrOrNone(c)

def getSshCommand():
    return copy.copy(_settings["SshCommand"])

def setPassCollections(collections):
    if collections is None:
        collections = [ ]
    if not (type(collections) == list):
        raise TypeError("Expecting a list")

    newColl = [ ]
    for c in collections:
        newColl.append(_checkPassCollection(c))

    _settings["PassCollections"] = newColl

def getPassCollections():
    return copy.deepcopy(_settings["PassCollections"])

def setPrivateKeys(keys):
    if keys is None:
        keys = [ ]
    if not (type(keys) == list):
        raise TypeError("Expecting a list")

    newKeys = [ ]
    for k in keys:
        newKeys.append(_checkPrivateKeyInfo(k))

    _settings["PrivateKeys"] = newKeys

def getPrivateKeys():
    return copy.deepcopy(_settings["PrivateKeys"])

def getFullSettingsString():
    return json.dumps(_settings, sort_keys=True, indent=4, separators=(',', ': '))

def setVersion(v):
    _settings["Version"] = _checkInt(v, 0, 1000)

def getVersion():
    return _settings["Version"]

def setAutoCheckIntervalMinutes(m):
    _settings["AutoCheckInterval"] = _checkInt(m, 0, 60*24)

def getAutoCheckIntervalMinutes():
    return _settings["AutoCheckInterval"]

def setAutoCheckReload(b):
    _settings["AutoCheckReload"] = _checkBoolean(b)

def getAutoCheckReload():
    return _settings["AutoCheckReload"]

