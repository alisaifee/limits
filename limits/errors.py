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
