import paramiko
import time
import select
import sys

class LineBuffer(object):
    def __init__(self, chan):
        self.chan = chan
        self.history = [ ]
        self.currentLine = b""
        self.fullLog = b""

    def poll(self):
        r, w, e = select.select([self.chan], [], [], 0.100)
        if self.chan in r:
            x = self.chan.recv(1024)
            if len(x) == 0:
                return False
            
            self.processBytes(x)

        return True

    def processBytes(self, x):

        for c in x:

            self.currentLine += bytes([c])
            self.fullLog += bytes([c])
            if c == ord('\n'):
                self.history.append(self.currentLine)
                self.currentLine = b""

    def waitFor(self, possibilities, timeout):
        startTime = time.time()
        while time.time() - startTime < timeout:
            self.poll()
            for s in possibilities:
                if s[-1] == ord('\n'):
                    if len(self.history) > 0 and s[:-1] in self.history[-1]:
                        matchLine = self.history[-1]
                        self.clear()
                        return (matchLine, s)
                else:
                    if s in self.currentLine:
                        matchLine = self.currentLine
                        self.clear()
                        return (matchLine, s)

        raise Exception("Timeout while waiting for " + repr(s))

    def clear(self):
        self.history = [ ]
        self.currentLine = b""

    def getFullLog(self):
        return self.fullLog

class SSHPasswordChanger(object):

    def __init__(self, user, host, port, oldPassword, newPassword):
        self.user = user
        self.host = host
        try:
            self.port = int(port)
        except:
            self.port = port

        self.oldPassword = oldPassword if type(oldPassword) == bytes else oldPassword.encode()
        self.newPassword = newPassword if type(newPassword) == bytes else newPassword.encode()
        self.lb = None

    def start(self):
        client = paramiko.SSHClient()
        #client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.onConnecting()
        client.connect(self.host, self.port, self.user, self.oldPassword, timeout = 15.0, allow_agent = False, look_for_keys = False)
        self.onConnected()
        chan = client.invoke_shell()

        self.onChangingPassword()
        self.changePassword(chan)

        chan = None
        client = None

        # Here we're making sure that the old password doesn't work anymore
        self.onVerifyingOldPasswordDisabled()
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.host, self.port, self.user, self.oldPassword, timeout = 15.0, allow_agent = False, look_for_keys = False)
            raise Exception("Unable to change old password: still works!")            
        except paramiko.ssh_exception.AuthenticationException as e:
            # Ok, this is expected since we used the wrong password
            pass
        
        client = None

        self.onTestingNewPassword()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.host, self.port, self.user, self.newPassword, timeout = 15.0, allow_agent = False, look_for_keys = False)
        client = None

    def changePassword(self, chan):
        chan.settimeout(0.0)
        lb = LineBuffer(chan)
        self.lb = lb

        chan.send(b"passwd\n")

        # For root, we don't have to type the old password
        oldPassStrings = [ b"Old password:", b"(current) UNIX password:" ]
        newPassStrings = [ b"ew password:", b"new UNIX password" ]

        (matchLine, matchString) = lb.waitFor(oldPassStrings + newPassStrings, 10.0)

        if matchString in oldPassStrings:
            chan.send(self.oldPassword + b"\n")
            lb.waitFor([ b"ew password:", b"new UNIX password" ], 5.0)
            chan.send(self.newPassword + b"\n")
            lb.waitFor([ b"ew password:", b"new UNIX password" ], 5.0)
            chan.send(self.newPassword + b"\n")
        else: # directly a new password
            chan.send(self.newPassword + b"\n")
            lb.waitFor([ b"ew password:", b"new UNIX password" ], 5.0)
            chan.send(self.newPassword + b"\n")

        lb.waitFor([ b"password changed", b"password updated successfully\n" ], 5.0)

        #print lb.getFullLog()

    def onConnecting(self):
        pass

    def onConnected(self):
        pass

    def onChangingPassword(self):
        pass

    def onVerifyingOldPasswordDisabled(self):
        pass

    def onTestingNewPassword(self):
        pass

    def getFullLog(self):
        if self.lb:
            return self.lb.getFullLog().decode()
        return ''

def main():
    spc = None
    try:
        spc = SSHPasswordChanger(*(sys.argv[1:]))
        spc.start()
        print("Password appears to be changed successfully")
    except:
        if spc:
            sys.stdout.write(spc.getFullLog() + "\n")
        sys.stdout.flush()
        raise

if __name__ == "__main__":
    main()
