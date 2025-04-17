#!/usr/bin/env python3

import sys
import argparse
import pandas as pd

sys.path.insert(0, "src")
from health_tracking.sheets import (
    get_sheets_client,
    create_spreadsheet,
    create_sheet,
    dataframe_to_sheet,
    append_to_sheet,
)


def main() -> None:
    """Command-line interface to demonstrate Google Sheets integration."""
    parser = argparse.ArgumentParser(description="Google Sheets Integration")
    parser.add_argument(
        "--create", type=str, help="Create a new spreadsheet with the given title"
    )
    parser.add_argument(
        "--csv-to-sheet", type=str, help="Path to a CSV file to upload to Google Sheets"
    )
    parser.add_argument(
        "--append-csv", type=str, help="Path to a CSV file to append to a Google Sheet"
    )
    parser.add_argument(
        "--spreadsheet-id", type=str, help="ID of an existing spreadsheet to use"
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        default="Sheet1",
        help="Name of the worksheet (default: Sheet1)",
    )
    parser.add_argument(
        "--create-sheet",
        action="store_true",
        help="Create the specified sheet if it doesn't exist",
    )

    args = parser.parse_args()

    # Get authenticated client
    sheets = get_sheets_client()

    spreadsheet_id = args.spreadsheet_id

    # Create a new spreadsheet if requested
    if args.create:
        spreadsheet_id = create_spreadsheet(sheets, args.create)

    # Create a new sheet if requested
    if args.create_sheet and spreadsheet_id:
        create_sheet(sheets, spreadsheet_id, args.sheet_name)

    # Upload CSV to sheet if requested
    if args.csv_to_sheet and spreadsheet_id:
        df = pd.read_csv(args.csv_to_sheet)
        print(f"Loaded {len(df)} rows from {args.csv_to_sheet}")
        dataframe_to_sheet(sheets, df, spreadsheet_id, args.sheet_name)

    # Append CSV to sheet if requested
    if args.append_csv and spreadsheet_id:
        df = pd.read_csv(args.append_csv)
        print(f"Loaded {len(df)} rows from {args.append_csv}")
        append_to_sheet(
            sheets,
            df,
            spreadsheet_id,
            args.sheet_name,
            include_header=(args.create_sheet),
        )

    # If no actions were requested, print help
    if not any(
        [
            args.create,
            args.csv_to_sheet and spreadsheet_id,
            args.append_csv and spreadsheet_id,
            args.create_sheet and spreadsheet_id,
        ]
    ):
        parser.print_help()


if __name__ == "__main__":
    main()
