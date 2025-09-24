class ModelInternalError(Exception):
    """Gen AI Model error."""
    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Model internal error"
        super().__init__(self.message)

    @property
    def default_answer(self) -> str:
        """Default answer when model raises this error."""
        return "I can't answer your question due to an internal error, please try again later."