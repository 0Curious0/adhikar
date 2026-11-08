class NLUError(Exception):
    """Base exception for NLU (intent/scheme decisions, entity extraction) failures."""


class NLURequestError(NLUError):
    def __init__(self, message: str, *, request_id: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.request_id = request_id
        self.status_code = status_code


class FieldSpecError(NLUError):
    """Raised when the same field name implies conflicting types across loaded schemes."""
