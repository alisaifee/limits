"""
errors and exceptions
"""


class ConfigurationError(Exception):
    """
    Error raised when a configuration problem is encountered
    """


class ConcurrentUpdateError(Exception):
    """
    Error raised when an update to limit fails due to concurrent
    updates
    """

    def __init__(self, key: str, attempts: int) -> None:
        super().__init__(f"Unable to update {key} after {attempts} retries")


class StorageError(Exception):
    """
    Error raised when an error is encountered in a storage
    """

    def __init__(self, storage_error: Exception) -> None:
        self.storage_error = storage_error
