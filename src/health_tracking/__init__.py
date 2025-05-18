"""Health tracking package for fetching fitness data and exporting to spreadsheets."""

import logging
import sys
from typing import Literal, Optional, Union

import colorlog

__version__ = "0.1.0"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def configure_logging(
    level: Union[LogLevel, int] = "INFO",
    format_string: Optional[str] = None,
    use_colors: bool = True,
) -> None:
    """
    Configure logging for the health_tracking package and its scripts.

    Args:
        level: Logging level, either as string or integer constant
        format_string: Optional custom format string for log messages
        use_colors: Whether to use colored output (requires colorlog package)
    """
    # Convert string log level to corresponding constant if needed
    if isinstance(level, str):
        numeric_level = getattr(logging, level)
    else:
        numeric_level = level

    # Use colored output if requested and available
    if use_colors:
        # Create a colored formatter
        if format_string is None:
            # Default color format string
            format_string = (
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        handler = colorlog.StreamHandler(sys.stdout)
        handler.setFormatter(
            colorlog.ColoredFormatter(
                format_string,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            )
        )

        # Get the root logger and configure it
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Remove existing handlers to avoid duplicate logs
        for h in root_logger.handlers:
            root_logger.removeHandler(h)

        # Add our colored handler
        root_logger.addHandler(handler)
    else:
        # Use default format if none provided
        if format_string is None:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Configure standard logging
        logging.basicConfig(
            level=numeric_level,
            format=format_string,
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,  # Ensure configuration is applied even if previously configured
        )


# Set up default logging configuration
configure_logging()

# Create a logger for this package
logger = logging.getLogger("health_tracking")
