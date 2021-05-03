CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
SUCCESS = 25
DEBUG = 10
TRACE = 5
NOTSET = 0


class RowdoException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.message = args[0]
        self.level = kwargs.get('level', DEBUG)


class ResizeException(RowdoException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ResizeModeException(RowdoException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RequestError(RowdoException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FileNameError(RowdoException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BlackListException(RowdoException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FileAccessError(RowdoException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
