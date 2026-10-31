class STTError(Exception):
    """Base exception for STT provider failures."""


class STTRequestError(STTError):
    def __init__(self, message: str, *, request_id: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.request_id = request_id
        self.status_code = status_code
