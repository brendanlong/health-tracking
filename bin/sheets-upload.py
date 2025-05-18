#!/usr/bin/env python3

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
from health_tracking import configure_logging
from health_tracking.sheets import (
    append_to_sheet,
    get_sheets_client,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Command-line interface to demonstrate Google Sheets integration."""
    parser = argparse.ArgumentParser(description="Google Sheets Integration")
    parser.add_argument(
        "--csv-in",
        type=Path,
        help="Path to a CSV file to upload to Google Sheets",
        required=True,
    )
    parser.add_argument(
        "--spreadsheet-id",
        type=str,
        help="ID of an existing spreadsheet to use",
        required=True,
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        default="Sheet1",
        help="Name of the worksheet (default: Sheet1)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored log output",
    )

    args = parser.parse_args()

    csv_in: str = args.csv_in
    spreadsheet_id: str = args.spreadsheet_id
    sheet_name: str = args.sheet_name

    # Configure logging
    configure_logging(args.log_level, use_colors=not args.no_color)

    # Get authenticated client
    sheets = get_sheets_client()

    # Upload CSV to sheet
    df = pd.read_csv(csv_in)
    logger.info(f"Loaded {len(df)} rows from {csv_in}")
    append_to_sheet(sheets, df, spreadsheet_id, sheet_name)


if __name__ == "__main__":
    main()
