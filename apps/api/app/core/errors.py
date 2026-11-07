class PaperError(Exception):
    """A paper-trading precondition failed; `code` is a stable identifier the web app maps to a message."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
