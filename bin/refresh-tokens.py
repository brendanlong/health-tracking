#!/usr/bin/env python3

import argparse
import logging
import sys

sys.path.insert(0, "src")
from health_tracking import configure_logging
from health_tracking.fitbit import get_fitbit_client
from health_tracking.sheets import get_sheets_client

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh Fitbit and Google Sheets authentication tokens"
    )

    parser.add_argument(
        "--fitbit-only", action="store_true", help="Only refresh Fitbit token"
    )
    parser.add_argument(
        "--google-only", action="store_true", help="Only refresh Google token"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored log output"
    )

    args = parser.parse_args()

    configure_logging(args.log_level, use_colors=not args.no_color)

    if args.fitbit_only and args.google_only:
        logger.error("Cannot specify both --fitbit-only and --google-only")
        sys.exit(1)

    refresh_fitbit = not args.google_only
    refresh_google = not args.fitbit_only

    if refresh_fitbit:
        logger.info("Refreshing Fitbit token...")
        try:
            get_fitbit_client()
            logger.info("Fitbit token refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh Fitbit token: {e}")
            sys.exit(1)

    if refresh_google:
        logger.info("Refreshing Google Sheets token...")
        try:
            get_sheets_client()
            logger.info("Google Sheets token refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh Google Sheets token: {e}")
            sys.exit(1)

    logger.info("Token refresh complete")


if __name__ == "__main__":
    main()
