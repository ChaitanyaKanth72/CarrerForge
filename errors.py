class AppError(Exception):
    """An error whose message is safe to show to the user."""
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status
