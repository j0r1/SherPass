#!/usr/bin/env python3

from sherpassexception import *
import os
import sys
import gnupg
import randomstring
import json
import copy
import sptempdir
import gpgdir
import threading
import multiprocessing
import time

def isPubKeyFileNameValid(fileName):
    if fileName[0] == ".":
        return False
    suffix = ".pubkey"
    if fileName[-len(suffix):].lower() != suffix:
        return False
    return True

def isPassFileNameValid(fileName):
    if fileName[0] == ".":
        return False
    suffix = ".pass"
    if fileName[-len(suffix):].lower() != suffix:
        return False
    return True

class SharedPass:

    rndStringLength = 16

    def __init__(self, privateKey, pubKeyDir, passDir, sync = True, passPhrase = None):

        self.gpgTempDir = sptempdir.getTempDir()
        print("Created directory {}".format(self.gpgTempDir), file=sys.stderr)

        gpg = gnupg.GPG(gpgbinary=gpgdir.gpg, gnupghome=self.gpgTempDir)

        gpg.import_keys(privateKey)
        
        privKeys = gpg.list_keys(True)
        if len(privKeys) != 1:
            raise SherPassException("There should be exactly one private key in the GPG keystore (is {})".format(len(privKeys)))

        pubKeys = gpg.list_keys(False)
        if len(pubKeys) != 1:
            raise SherPassException("There should not be any extra public keys present during initialization (private key file contains other public key data?)")

        self.ownFingerPrint = privKeys[0]["fingerprint"]
        
        self.gpg = gpg
        self.pubKeyDir = pubKeyDir
        self.passDir = passDir
        self.passInfo = [ ]
        self.passPhrase = passPhrase
        
        self.pubkeyFiles = { }
        self.passFiles = { }

        self.foundOwnPubkeyFiles = [ ]

        if sync:
            self.syncPublicKeys()
            self.syncPassInfo()

    def __del__(self): # Must delete the temporary directory again
        files = os.listdir(self.gpgTempDir)
        for f in files:
            fullName = os.path.join(self.gpgTempDir, f)
            os.unlink(fullName)
            print("Removed {}".format(fullName), file=sys.stderr)

        os.rmdir(self.gpgTempDir)
        print("Removed {}".format(self.gpgTempDir), file=sys.stderr)

    def getOwnFingerprint(self):
        return self.ownFingerPrint

    def setPassPhrase(self, passPhrase):
        self.passPhrase = passPhrase

    def _extractPubKeyData(self, data):

        if type(data) != str:
            raise SherPassExceptionNeedString("'_extractPubKeyData' needs string as input")
    
        lines = [ l.strip() for l in data.splitlines() ]
        for i,l in enumerate(lines[:]):
            if l == "-----BEGIN PGP PUBLIC KEY BLOCK-----":
                del lines[:i+1+2] # Also remove Version line and blank line, not sure how generally valid this is
                break

        #print(lines)
        s = ""
        for l in lines:
            if l == "-----END PGP PUBLIC KEY BLOCK-----":
                break
            s += l

        #print(s)
        #print()
        return s

    def syncPublicKeys(self):

        self.foundOwnPubkeyFiles = [ ]
        self.pubkeyFiles = { }
        ownKeyData = self._extractPubKeyData(self.exportPublicKey().decode())

        gpg = self.gpg

        oldFingerprints = set()
        pubKeys = gpg.list_keys()
        for p in pubKeys:
            fp = p["fingerprint"]
            if fp != self.ownFingerPrint:
                oldFingerprints.add(fp)
        
        pubKeyFiles = [ i for i in os.listdir(self.pubKeyDir) if not i.startswith(".") ]
        importedFingerPrints = set()
        for fileName in pubKeyFiles:
            if not isPubKeyFileNameValid(fileName):
                raise SherPassException("Invalid public key filename: " + fileName)

            fullFileName = os.path.join(self.pubKeyDir,fileName)
            with open(fullFileName,"rb") as f:
                keyData = f.read()

            fileSize, fileTime = self.getSizeAndModificationTime(fullFileName)
            self.pubkeyFiles[fileName] = { "Size": fileSize, "Time": fileTime }

            if self._extractPubKeyData(keyData.decode()) == ownKeyData:
                self.foundOwnPubkeyFiles.append(fileName)

            pubKeys = gpg.import_keys(keyData)
            for fp in pubKeys.fingerprints:
                importedFingerPrints.add(fp)

        privKeys = gpg.list_keys(True)
        if len(privKeys) != 1: # Remove the other private keys again
            delKeys = ""
            for k in privKeys:
                fp = k["fingerprint"]
                if fp != self.ownFingerPrint:
                    delKeys += " " + fp
                    gpg.delete_keys([fp],True) # Private key
                    gpg.delete_keys([fp])      # Public key (if it exists)

            raise SherPassException("Imported other private keys (deleted them again):" + delKeys)

        if not self.ownFingerPrint in importedFingerPrints:
            raise SherPassExceptionOwnPubKeyNotFound("Own public key is not among the imported keys")

        # Remove the fingerprints from our keystore that are no longer in the
        # key directory

        for fp in oldFingerprints:
            if not fp in importedFingerPrints: # Own key is also imported
                gpg.delete_keys([fp])

    def listPublicKeys(self):
        gpg = self.gpg
        pubKeys = gpg.list_keys()
        keyList = [ ]
        for k in pubKeys:
            keyList.append( (k["fingerprint"], k["uids"][0]) )

        return keyList
                
    def exportPublicKey(self):
        gpg = self.gpg
        s = str(gpg.export_keys([self.ownFingerPrint]))
        if not s:
            raise SherPassException("Could not find public key with own fingerprint in keystore")

        return s.encode()

    def exportPrivateKey(self):
        gpg = self.gpg
        s = str(gpg.export_keys([self.ownFingerPrint], True))
        if not s:
            raise SherPassException("Could not find private key with own fingerprint in keystore")

        return s.encode()

    def encrypt(self, s, fingerPrints):

        if type(s) != bytes:
            raise SherPassExceptionNeedBytes("'encrypt' needs bytes as input")

        #print "SharedPass.encrypt: ", fingerPrints
        #print "data:", s

        s = randomstring.getRandomString(self.rndStringLength).encode() + s

        gpg = self.gpg
        pubKeys = gpg.list_keys()
        fpList = [ ]

        if not fingerPrints: # Means all known fingerprints
            for k in pubKeys:
                fpList.append(k["fingerprint"])
        else:
            knownPrints = set([ k["fingerprint"] for k in pubKeys ])
            for k in fingerPrints:
                if k in knownPrints:
                    fpList.append(k)
                else:
                    raise SherPassException("An unknown fingerprint was specified")

            if not self.ownFingerPrint in fpList:
                raise SherPassException("Own fingerprint not specified, disallowing encoding data that we can't decode ourselves")

        # TODO: Not sure how safe this 'always trust' is in this scenario. Didn't need it when using a
        #       gpg keyring from the start, but do need it when just starting from scratch and importing
        #       a private key

        #print "fpList", fpList

        encData = str(gpg.encrypt(s, fpList, always_trust=True)) 
        if not encData:
            raise SherPassException("Error encrypting data (invalid key fingerprint?)")

        return encData.encode()

    def decrypt(self, s):

        if type(s) != bytes:
            raise SherPassExceptionNeedBytes("'decrypt' needs bytes as input")

        gpg = self.gpg
        if not self.passPhrase:
            decData = str(gpg.decrypt(s))
        else:
            decData = str(gpg.decrypt(s,passphrase=self.passPhrase))

        if not decData:
            raise SherPassException("Unable to decode specified data")

        if len(decData) < self.rndStringLength:
            raise SherPassException("Invalid decode result")

        return decData[self.rndStringLength:].encode()

    def _processFileToLoad(self, filesToLoad, decodedEntries):

        envName = "SHERPASS_NUMTHREADS"
        if envName in os.environ:
            try:
                numThreads = int(os.environ[envName])
            except Exception as e:
                print("""Exception: {}

Warning: SHERPASS_NUMTHREADS is an environment variable, but can't interpret
as number of threads. Defaulting to 1.""".format(e))
                numThreads = 1
        else:
            numThreads = multiprocessing.cpu_count() * 2 # TODO: does the *2 make a difference

        groups = [ [] for i in range(numThreads) ]

        pos = 0
        for x in filesToLoad:
            groups[pos%numThreads].append(x)
            pos += 1

        def bgproc(i):

            filesToLoad = groups[i]

            for fileName,fullFileName,fileSize,fileTime in filesToLoad:
                # print("Loading information for {}".format(fileName))
                with open(fullFileName, "rb") as f:
                    data = f.read()
                    f.close()

                decData = None
                try:
                    decData = self.decrypt(data)
                    if decData:
                        decObj = json.loads(decData.decode())
                except SherPassException as e:
                    print(fileName, e)

                entry = { 
                    "FileName": fileName, 
                    "Decoded": decObj, 
                    "Size": fileSize,
                    "Time": fileTime
                }
                
                decodedEntries.append(entry)

        threads = [ ]
        for i in range(numThreads):
            t = threading.Thread(target = bgproc, args = (i, ))
            threads.append(t)

        print("Decoding {} entries using {} threads".format(len(filesToLoad), numThreads))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def syncPassInfo(self):

        startTime = time.time()

        oldPassInfo = self.passFiles
        self.passFiles = { }
        self.passInfo = [ ]
        
        passFiles = [ i for i in os.listdir(self.passDir) if not i.startswith(".") ]
        passFiles = [ fileName for fileName in passFiles if isPassFileNameValid(fileName) and len(fileName) == 16+1+4 ]

        filesToLoad = [ ] 
        decodedEntries = [ ]
        
        for fileName in passFiles:
            #if not self.isPassFileNameValid(fileName):
            #    raise SherPassException("Invalid password filename: " + fileName)

            fullFileName = os.path.join(self.passDir,fileName)
            fileSize, fileTime = self.getSizeAndModificationTime(fullFileName)

            decObj = None
            loadFile = True
            if fileName in oldPassInfo:
                oldEntry = oldPassInfo[fileName]
                if fileSize is not None and fileTime is not None and oldEntry["Size"] is not None and oldEntry["Time"] is not None:
                    if fileSize == oldEntry["Size"] and fileTime == oldEntry["Time"]:
                        loadFile = False
                        decObj = oldEntry["Decoded"]
                        # print("Reusing information for {}".format(fileName))

            if loadFile:
                filesToLoad.append((fileName, fullFileName, fileSize, fileTime))
            else:
                entry = { 
                    "FileName": fileName, 
                    "Decoded": decObj, 
                    "Size": fileSize,
                    "Time": fileTime
                }

                decodedEntries.append(entry)

        self._processFileToLoad(filesToLoad, decodedEntries)

        for entry in decodedEntries:
            fileName = entry["FileName"]
            decObj = entry["Decoded"]

            self.passFiles[fileName] = entry
            if decObj:
                self.passInfo.append(entry)

        dt = time.time() - startTime
        print("Synced password info in {} seconds".format(dt))

    def listPasswords(self):
        return [ (p["FileName"], p["Decoded"] ) for p in copy.deepcopy(self.passInfo) ]

    def addPassword(self, obj, fingerPrints = None): # None means all known fingerprints
        s = json.dumps(obj).encode()
        enc = self.encrypt(s, fingerPrints)
        fileName = randomstring.getRandomString(16) + ".pass"
        fullFileName = os.path.join(self.passDir,fileName)

        if os.path.exists(fullFileName):
            raise SherPassException("Randomly generated filename already seems to exist: " + fileName)

        with open(fullFileName, "wb") as f:
            f.write(enc)
            f.close()

        decObj = json.loads(s.decode())
        fileSize, fileTime = self.getSizeAndModificationTime(fullFileName)

        newEntry = {
            "FileName": fileName, 
            "Decoded": decObj, 
            "Size": fileSize,
            "Time": fileTime
        }

        self.passInfo.append(newEntry)
        self.passFiles[fileName] = newEntry

        return copy.deepcopy((fileName, decObj))

    def updatePassword(self, fileName, obj, fingerPrints = None): # None just means all loaded prints

        entryIdx = -1
        for idx in range(len(self.passInfo)):
            if self.passInfo[idx]["FileName"] == fileName:
                entryIdx = idx
                break

        if entryIdx < 0:
            raise SherPassException("No entry with the specified filename found: " + fileName)

        s = json.dumps(obj).encode()
        enc = self.encrypt(s, fingerPrints)
        fullFileName = os.path.join(self.passDir,fileName)

        if not os.path.exists(fullFileName):
            raise SherPassException("Specified filename does not yet exist: " + fileName)

        with open(fullFileName, "wb") as f:
            f.write(enc)
            f.close()

        decObj = json.loads(s.decode())
        fileSize, fileTime = self.getSizeAndModificationTime(fullFileName)

        newEntry = {
            "FileName": fileName, 
            "Decoded": decObj, 
            "Size": fileSize,
            "Time": fileTime
        }

        entries = self.passInfo

        self.passInfo = entries[:entryIdx] + [ newEntry ] + entries[entryIdx+1:]
        self.passFiles[fileName] = newEntry

        return copy.deepcopy((fileName, decObj))

    def removePassword(self, fileName):

        entryIdx = -1
        for idx in range(len(self.passInfo)):
            if self.passInfo[idx]["FileName"] == fileName:
                entryIdx = idx
                break

        if entryIdx < 0:
            raise SherPassException("No entry with the specified filename found: " + fileName)

        fullFileName = os.path.join(self.passDir, fileName)
        os.unlink(fullFileName)
        entries = self.passInfo

        self.passInfo = entries[:entryIdx] + entries[entryIdx+1:]
        del self.passFiles[fileName]

    def getSizeAndModificationTime(self, fullFileName):
        fileSize = None
        fileTime = None

        try:
            fileSize = os.path.getmtime(fullFileName)
            fileTime = os.path.getsize(fullFileName)
        except Exception as e:
            print("Warning: can't get property of file {}: {}".format(fullFileName, str(e)))

        return (fileSize, fileTime)

    def hasDifferentKeys(self):
        
        pubKeyFiles = [ i for i in os.listdir(self.pubKeyDir) if not i.startswith(".") ]
        for fileName in pubKeyFiles:
            if not isPubKeyFileNameValid(fileName):
                return True

            fullFileName = os.path.join(self.pubKeyDir,fileName)
            fileSize, fileTime = self.getSizeAndModificationTime(fullFileName)

            if not fileName in self.pubkeyFiles:
                return True

            oldEntry = self.pubkeyFiles[fileName]
            if fileSize != oldEntry["Size"] or fileTime != oldEntry["Time"]:
                return True

        # Check if a key disappeared
        newFiles = set(pubKeyFiles)
        for n in self.pubkeyFiles:
            if not n in newFiles:
                return True

        return False

    def hasDifferentPasswordEntries(self):

        oldPassInfo = self.passFiles

        passFiles = [ i for i in os.listdir(self.passDir) if not i.startswith(".") ]
        passFiles = [ fileName for fileName in passFiles if isPassFileNameValid(fileName) and len(fileName) == 16+1+4 ]
        
        for fileName in passFiles:

            fullFileName = os.path.join(self.passDir,fileName)
            fileSize, fileTime = self.getSizeAndModificationTime(fullFileName)

            if not fileName in oldPassInfo:
                return True

            oldEntry = oldPassInfo[fileName]
            if fileSize is None or fileTime is None or oldEntry["Size"] is None or oldEntry["Time"] is None:
                return True

            if fileSize != oldEntry["Size"] or fileTime != oldEntry["Time"]:
                return True

        # We also need to check if a file disappeared
        newFiles = set(passFiles)
        for n in oldPassInfo:
            if not n in newFiles:
                return True

        return False

    def clearPassphrase(self):
        self.passPhrase = None
        self.passInfo = [ ]
        self.passFiles = { }

if __name__ == "__main__":

    tempDirBase = sys.argv[1]
    privKeyFile = sys.argv[2]
    pubKeyDir = sys.argv[3]
    passDir = sys.argv[4]

    sptempdir.setTempDirBase(tempDirBase)
    privKey = open(privKeyFile, "rb").read()

    sp = SharedPass(privKey, pubKeyDir, passDir)

    print(sp.foundOwnPubkeyFiles)

