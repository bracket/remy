class RemyError(Exception):
    pass


class InvalidComparison(RemyError):
    """Raised when attempting to compare incompatible types."""
    pass
