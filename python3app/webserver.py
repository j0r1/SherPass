from PyQt5 import QtCore, QtNetwork, QtGui
from sherpassexception import SherPassException
import sys
import time
import aescrypt

class SSLTcpServer(QtNetwork.QTcpServer):

    def __init__(self, webServer):
        super(SSLTcpServer, self).__init__(webServer)
        self.sslCertificate = None
        self.sslKey = None
        self.webServer = webServer
        self.sockets = set()

    def setSSLInfo(self, cert, key):
        self.sslCertificate = cert
        self.sslKey = key

    def incomingConnection(self, sockDesc):
        #print("Incoming connection: {}".format(sockDesc))

        sslSocket = QtNetwork.QSslSocket()
        if sslSocket.setSocketDescriptor(sockDesc):

            sslConf = sslSocket.sslConfiguration()
            sslConf.setPeerVerifyMode(QtNetwork.QSslSocket.VerifyNone)
            sslConf.setLocalCertificate(self.sslCertificate)
            sslConf.setPrivateKey(self.sslKey)
            sslSocket.setSslConfiguration(sslConf)

            self.addPendingConnection(sslSocket)

            sslSocket.encrypted.connect(self.webServer.onEncrypted)
            sslSocket.startServerEncryption()

            self.sockets.add(sslSocket)

    def removeSavedSocket(self, sock):
        try:
            self.sockets.remove(sock)
        except Exception as e:
            print("SSLTcpServer.removeSavedSocket: WARNING: {}".format(e))

class WebServer(QtCore.QObject):

    signalTooManyBadConnections = QtCore.pyqtSignal(int)
    signalLog = QtCore.pyqtSignal(str)

    def __init__(self, messageBytesFunction, maxBadConnections = 10, parent = None):
        super(WebServer, self).__init__(parent)
        self.connections = [ ]
        self.oldConnections = [ ]
        self.serverSocket = None
        self.isSsl = False
        self.badConnectionCount = 0
        self.maxBadConnections = maxBadConnections
        self.getMessageBytes = messageBytesFunction
        self.isStarted = False

    def _scheduleAsync(self, function):

        t = QtCore.QTimer(self)

        def f():
            t.timeout.disconnect(f)
            function()

        t.timeout.connect(f)
        t.setSingleShot(True)
        t.start(0)

    def startHTTPS(self, port, url, aesKey, sslCertificate, sslKey):
        if self.isStarted:
            raise SherPassException("WebServer object is already started")

        if sslCertificate.isNull():
            raise SherPassException("Specified certificate is invalid")
        if sslKey.isNull():
            raise SherPassException("Specified SSL key is invalid")

        self.isSsl = True
        self.serverSocket = SSLTcpServer(self)
        self.serverSocket.setSSLInfo(sslCertificate, sslKey)
        self._commonStart(port, url, aesKey)

    def startHTTP(self, port, url, aesKey):
        if self.isStarted:
            raise SherPassException("WebServer object is already started")

        self.isSsl = False
        self.serverSocket = QtNetwork.QTcpServer(self)
        self._commonStart(port, url, aesKey)

    def _commonStart(self, port, url, aesKey):

        self.serverSocket.newConnection.connect(self.onNewConnection) 

        if (type(url) is not bytes) or (type(aesKey) is not bytes):
            raise SherPassException("Access URL and AES key must be specified as bytes")

        if not self.serverSocket.listen(QtNetwork.QHostAddress.LocalHost, port):
            raise SherPassException("Can't start listening on port {}".format(port))

        self.connCheckTimer = QtCore.QTimer(self)
        self.connCheckTimer.timeout.connect(self.onConnectionCheck)
        self.connCheckTimer.start(10000)

        self.accessUrl = url
        self.aesKey = aesKey
        self.isStarted = True

    def onEncrypted(self):
        #print("onEncrypted")
        conn = self.sender()
        conn.readyRead.connect(self.onReadyRead)

    def onNewConnection(self):
        #print("onNewConnection")
        conn = self.serverSocket.nextPendingConnection()

        self.connections.append( (conn, time.time()) )
        if self.isSsl:
            self.serverSocket.removeSavedSocket(conn)

        conn.headerLines = [ ]
        conn.doneReading = False

        if (self.isSsl and conn.isEncrypted()) or not self.isSsl:
            conn.readyRead.connect(self.onReadyRead)
        
        conn.disconnected.connect(self.onDisconnected) # Also emitted when _we_ close the connection
        
        msg = "New connection from: " + conn.peerAddress().toString() + ":" + str(conn.peerPort())
        self._log(msg)

    def onReadyRead(self):
        #print("onReadyRead")
        conn = self.sender()

        while conn.canReadLine():
            l0 = conn.readLine()
            if conn.doneReading:
                continue

            l = bytes(l0).rstrip()
            #print("Received:", l)

            if len(conn.headerLines) == 0:
                parts = l.split(b" ")   
                if len(parts) != 3 or not parts[0] in [ b"GET", b"OPTIONS" ]:
                    self._log("Invalid header line '{}' from {}:{}".format(l,conn.peerAddress().toString(),conn.peerPort()))
                    conn.doneReading = True 
                    conn.close()
                    self.badConnectionCount += 1

                    if self.badConnectionCount >= self.maxBadConnections:
                        self._scheduleAsync(self._onTooManyBadConnections)

                    return

                conn.requestType = parts[0]
                conn.requestLocation = parts[1]

            if len(l) == 0:
                conn.doneReading = True
                self.analyzeRequest(conn)
            elif len(l) < 1024 and len(conn.headerLines) < 1024:
                conn.headerLines.append(l)

    def _log(self, msg):
        print(msg)
        self.signalLog.emit(msg)

    def _removeSocketSignalConnections(self, sock):

        try: sock.encrypted.disconnect(self.onEncrypted)
        except: pass

        try: sock.newConnection.disconnect(self.onNewConnection)
        except: pass

        try: sock.disconnected.disconnect(self.onDisconnected)
        except: pass

        try: sock.readyRead.disconnect(self.onReadyRead)
        except: pass

    def onDisconnected(self):
        #print("onDisconnected")

        conn = self.sender()
        self._log("Closed connection for {}:{}".format(conn.peerAddress().toString(),conn.peerPort()))

        idx = -1
        for i in range(len(self.connections)):
            if self.connections[i][0] == conn:
                idx = i
                break

        if idx < 0:
            print("onDisconnected: connection not found")
        else:
            #print("Deleting connection")
            self._removeSocketSignalConnections(self.connections[idx][0])
            self.oldConnections.append(self.connections[idx])
            del self.connections[idx]
            #print("Done")

    def analyzeRequest(self, conn):
        #print("analyzeRequest")
        
        headers = { }

        for l in conn.headerLines[1:]:
            idx = l.find(b":")
            if idx > 0:
                headers[l[:idx].lower()] = l[idx+1:]
        
        def startResponse(line, headers):
            response = line + b"\r\n"
            response += b"Access-Control-Allow-Origin: *\r\n"
            x = b"access-control-request-headers"

            if x in headers:
                response += b"Access-Control-Allow-Headers:" + headers[x]
                response += b"\r\n"

            return response

        if conn.requestType == b"OPTIONS":
            response = startResponse(b"HTTP/1.1 200 OK", headers)
            response += b"Content-length: 0\r\n\r\n"
        else:

            idx = conn.requestLocation.find(b"?")
            subLocation = conn.requestLocation[:idx] if idx >= 0 else conn.requestLocation
            
            accessUrl = b"/" + self.accessUrl
            if subLocation != accessUrl:
                response = startResponse(b"HTTP/1.1 404 Not found", headers)
                self.badConnectionCount += 1
                self._log("Connection {}:{} requested invalid location {}".format(conn.peerAddress().toString(),conn.peerPort(),subLocation))

                if self.badConnectionCount >= self.maxBadConnections:
                    self._scheduleAsync(self._onTooManyBadConnections)

            else:
                response = startResponse(b"HTTP/1.1 200 OK", headers)
                response += b"Content-type: image/png\r\n"

                body = self.getMessageBytes() # A subclass should override the default!
                body = aescrypt.encrypt(body, self.aesKey)
                
                width = 1024
                numLines = len(body)//(width*3) + 1
                totalLen = (width*3)*numLines

                restLen = totalLen - len(body)
                body += b' ' * restLen

                # Encode as an image so we can use an Image() in we web page to retrieve
                # this instead of an XHR

                img = QtGui.QImage(width, numLines, QtGui.QImage.Format_RGB32)
                for y in range(numLines):
                    for x in range(width):
                        idx = (x + y*width)*3

                        r = int(body[idx])
                        g = int(body[idx+1])
                        b = int(body[idx+2])

                        img.setPixel(x, y, QtGui.qRgb(r,g,b))

                ba = QtCore.QByteArray()
                buf = QtCore.QBuffer(ba)
                buf.open(QtCore.QIODevice.WriteOnly)
                img.save(buf, "PNG")
                
                response += "Content-length: {}\r\n\r\n".format(len(ba)).encode()
                response += ba
                
                self._log("Sent password entries to {}:{}".format(conn.peerAddress().toString(),conn.peerPort()))

                # Everything OK, reset count
                self.badConnectionCount = 0

        conn.write(response)
        conn.flush()
        conn.close()

    def _onTooManyBadConnections(self):
        #print("_onTooManyBadConnections")
        self.close()
        self.signalTooManyBadConnections.emit(self.badConnectionCount)

    def close(self):

        #print("close")
        if self.serverSocket:
            self._removeSocketSignalConnections(self.serverSocket)
            self.connCheckTimer.timeout.disconnect(self.onConnectionCheck)
            self.serverSocket.close()
            self.serverSocket = None

            for (c, t) in self.connections:
                self._removeSocketSignalConnections(c)

            self.connections = [ ]

    def onConnectionCheck(self): # We'll do one at a time for simplicity
        #print("onConnectionCheck")
        #print("webserver.connection:")
        #print(self.connections)
        #if self.isSsl and self.serverSocket:
        #    print("serverSocket.sockets")
        #    print(self.serverSocket.sockets)

        t = time.time()

        # This causes the old objects to be removed
        self.oldConnections = [ ]

        idx = 0
        while idx < len(self.connections):
            (c, t0) = self.connections[idx]
            if c and t - t0 > 10:
                self._log("Timeout for connection {}:{}".format(c.peerAddress().toString(),c.peerPort()))

                self._removeSocketSignalConnections(c)
                c.close()

                self.oldConnections.append(c)
                del self.connections[idx]
            else:
                idx += 1

def main():
    app = QtCore.QCoreApplication(sys.argv)

    certFile = QtCore.QFile("server.pem")
    keyFile = QtCore.QFile("server.pem")
    certFile.open(QtCore.QIODevice.ReadOnly)
    keyFile.open(QtCore.QIODevice.ReadOnly)
    sslCert = QtNetwork.QSslCertificate(certFile, QtNetwork.QSsl.Pem)
    sslKey = QtNetwork.QSslKey(keyFile, QtNetwork.QSsl.Rsa, QtNetwork.QSsl.Pem)

    def msgFn():
        return b"12345"

    w = WebServer(msgFn, 10)
    w.signalTooManyBadConnections.connect(app.quit)
    #w.startHTTPS(12345, b"1", b"1", sslCert, sslKey)
    w.startHTTP(12345, b"1", b"1")
    app.exec_()

if __name__ == "__main__":
    main()
