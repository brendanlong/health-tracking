#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
from health_tracking.sheets import (
    append_to_sheet,
    get_sheets_client,
)


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

    args = parser.parse_args()

    # Get authenticated client
    sheets = get_sheets_client()

    spreadsheet_id = args.spreadsheet_id

    # Upload CSV to sheet
    df = pd.read_csv(args.csv_in)
    print(f"Loaded {len(df)} rows from {args.csv_in}")
    append_to_sheet(sheets, df, spreadsheet_id, args.sheet_name)


if __name__ == "__main__":
    main()
