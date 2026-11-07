class SchemeError(Exception):
    """Base exception for scheme knowledge-base failures."""


class SchemeLoadError(SchemeError):
    """Raised when one or more scheme files fail to load or validate.

    `str(error)` lists every failing file, not just the first one.
    """