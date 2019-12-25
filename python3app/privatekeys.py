from sherpassexception import SherPassException, SherPassExceptionUnknownFingerprint, SherPassExceptionNoPassphrase
import copy

_privateKeys = [ ]

def appendEntry(fileName, keyName):
    keyInfo = { 
        "fingerprint": None,
        "filename": fileName,
        "name": keyName,
        "data": None,
        "passphrase": None,
    }

    _privateKeys.append(keyInfo)
    return keyInfo

def getKeys(createCopy = True):
    if createCopy:
        return copy.deepcopy(_privateKeys)
    return _privateKeys

def getKeyAndPassphrase(fingerprint):
    if not fingerprint:
        raise SherPassException("No fingerprint specified")

    encounteredFingerprint = False
    encounteredKeyData = False
    for k in _privateKeys:
        if k["fingerprint"] == fingerprint:
            encounteredFingerprint = True
            if k["data"] is not None:
                encounteredKeyData = True
                if k["passphrase"] is not None:
                    return(k["data"], k["passphrase"])

    if not encounteredFingerprint:
        raise SherPassExceptionUnknownFingerprint("Specified key fingerprint is not one of the loaded private keys")
    if not encounteredKeyData:
        raise SherPassException("Relevant private key data could not be loaded")

    raise SherPassExceptionNoPassphrase("Invalid passphrase for the private key")

def clear():
    del _privateKeys[:]

def getFingerprints():
    fp = set([ k["fingerprint"] for k in _privateKeys if k["fingerprint"] and k["data"] ])
    fp = sorted([ x for x in fp ])
    return fp

def getKeysForFingerprint(fp, createCopy = True):
    l = [ k for k in _privateKeys if k["fingerprint"] == fp ]

    def sortFunction(k):
        return k["name"].lower() + k["filename"]

    l = sorted(l, key=sortFunction)
    if createCopy:
        l = copy.deepcopy(l)
    return l

