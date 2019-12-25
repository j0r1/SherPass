# from http://stackoverflow.com/questions/8806481/how-can-i-decrypt-something-with-pycrypto-that-was-encrypted-using-openssl

from base64 import b64decode, b64encode
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto import Random

def generateKeyAndIV(secret, salt):

    # We need 32 bytes for the AES key, and 16 bytes for the IV
    def openssl_kdf(req):
        prev = b''
        while req > 0:
            prev = MD5.new(prev+secret+salt).digest()
            req -= 16
            yield prev


    mat = b''.join([ x for x in openssl_kdf(32+16) ])
    key = mat[0:32]
    iv  = mat[32:48]

    return (key, iv)

def decrypt(base64encoded, secret):
    encrypted = b64decode(base64encoded)
    salt = encrypted[8:16]
    data = encrypted[16:]

    (key, iv) = generateKeyAndIV(secret, salt)

    dec = AES.new(key, AES.MODE_CBC, iv)
    return dec.decrypt(data)

def encrypt(inputData, secret):
    salt = Random.new().read(8)
    (key, iv) = generateKeyAndIV(secret, salt)

    encrypted = bytes.fromhex('53616c7465645f5f') # First eight bytes are 'Salted__'
    encrypted += salt

    enc = AES.new(key, AES.MODE_CBC, iv)
    diff = 16-len(inputData)%16
    inputData += chr(diff).encode()*diff # padding
    encrypted += enc.encrypt(inputData)

    return b64encode(encrypted)

def main():
    msg = b"My very secret message"
    encrypted = encrypt(msg, b'secretpassphrase')
    print(encrypted)
    print(repr(decrypt(encrypted, b'secretpassphrase')))

if __name__ == "__main__":

    main()

