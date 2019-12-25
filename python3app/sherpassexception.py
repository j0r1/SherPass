class SherPassException(Exception):
    pass

class SherPassExceptionOwnPubKeyNotFound(SherPassException):
    pass

class SherPassExceptionNeedBytes(SherPassException):
    pass

class SherPassExceptionNeedString(SherPassException):
    pass

class SherPassExceptionNoConfig(SherPassException):
    pass

class SherPassExceptionUnknownFingerprint(SherPassException):
    pass

class SherPassExceptionNoPassphrase(SherPassException):
    pass
