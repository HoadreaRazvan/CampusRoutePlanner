from typing import Optional


class InputValidationError(ValueError):
    """Raised when an input file is rejected. `code` is a stable identifier, e.g. INVALID_EDGE_WEIGHT."""

    def __init__(self, code: str, message: str, path: Optional[str] = None, line: Optional[int] = None):
        self.code = code
        self.path = path
        self.line = line
        location = ""
        if path:
            location = f" ({path}" + (f", line {line}" if line is not None else "") + ")"
        super().__init__(f"{code}: {message}{location}")
