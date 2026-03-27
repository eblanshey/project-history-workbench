# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Utility functions and classes for the Diff Workbench.
"""Utility functions and classes for the Diff Workbench.

This module contains shared utilities including the unified logging system.
"""

from typing import Protocol


class Logger(Protocol):
    """Logger protocol for consistent logging interface.

    This protocol defines the standard logging methods used throughout
    the application. All logger implementations must conform to this interface.
    """

    def debug(self, message: str) -> None:
        """Log a debug message."""
        ...

    def info(self, message: str) -> None:
        """Log an informational message."""
        ...

    def warning(self, message: str) -> None:
        """Log a warning message."""
        ...

    def error(self, message: str) -> None:
        """Log an error message."""
        ...


class StdoutLogger:
    """Logger that outputs to stdout/stderr.

    This is the default logger used before the application initializes its
    production logger. Useful for testing or CLI scenarios where FreeCAD
    console is not available.
    """

    def debug(self, message: str) -> None:
        """Log a debug message to stdout."""
        print(f"DEBUG: {message}")

    def info(self, message: str) -> None:
        """Log an informational message to stdout."""
        print(message)

    def warning(self, message: str) -> None:
        """Log a warning message to stdout."""
        print(f"WARNING: {message}")

    def error(self, message: str) -> None:
        """Log an error message to stderr."""
        print(f"ERROR: {message}", flush=True)


# Global logger instance - starts as StdoutLogger to ensure messages aren't lost
_logger: Logger = StdoutLogger()


def set_logger(logger: Logger) -> None:
    """Set the global logger instance.

    This should be called once during application startup (in workbench.Initialize()).
    After initialization, all logging calls will use the configured logger.

    Args:
        logger: The logger instance to use for all logging operations
    """
    global _logger
    _logger = logger


class Log:
    """Convenience class for accessing the global logger.

    Provides static methods for logging that delegate to the global logger
    instance. This avoids importing multiple functions and provides a
    cleaner API.

    Usage:
        Log.info("Informational message")
        Log.warning("Warning message")
        Log.error("Error message")
        Log.debug("Debug message")
    """

    @staticmethod
    def debug(message: str) -> None:
        """Log a debug message.

        Args:
            message: The message to log
        """
        _logger.debug(message)

    @staticmethod
    def info(message: str) -> None:
        """Log an informational message.

        Args:
            message: The message to log
        """
        _logger.info(message)

    @staticmethod
    def warning(message: str) -> None:
        """Log a warning message.

        Args:
            message: The message to log
        """
        _logger.warning(message)

    @staticmethod
    def error(message: str) -> None:
        """Log an error message.

        Args:
            message: The message to log
        """
        _logger.error(message)


__all__ = [
    "Logger",
    "StdoutLogger",
    "Log",
    "set_logger",
]
