from app.enums import ExceptionAlias


class ClusterBuilderException(Exception):
    _exception_alias = ExceptionAlias.UndefinedError
    error: str = None

    def __init__(self, details: str, *, error: str = None):
        self.error = error
        super().__init__(details)
