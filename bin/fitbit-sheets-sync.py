#!/usr/bin/env python3

import argparse
import logging
import sys
from datetime import date, timedelta
from typing import Literal, Optional

import pandas as pd

sys.path.insert(0, "src")
from health_tracking import configure_logging
from health_tracking.fitbit import (
    get_fitbit_client,
    get_resting_heart_rate,
    get_sleep_data,
)
from health_tracking.sheets import (
    NoSuchSheetException,
    append_to_sheet,
    get_sheets_client,
    sheet_to_dataframe,
    sheets_link,
)

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync data from Fitbit to Google Sheets"
    )

    # Data type argument
    parser.add_argument(
        "--type",
        type=str,
        choices=["sleep", "heart-rate"],
        default="sleep",
        help="Type of data to fetch (sleep or heart-rate)",
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
        "--default-days",
        "-d",
        type=int,
        help="Number of days to look back if we're creating a new sheet.",
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

    # Configure logging
    configure_logging(args.log_level, use_colors=not args.no_color)

    data_type: Literal["sleep", "heart-rate"] = args.type
    sheet_id: str = args.spreadsheet_id
    sheet_name: str = args.sheet_name
    default_days: Optional[int] = args.default_days

    # Get authenticated client
    fitbit_client = get_fitbit_client()
    sheets_client = get_sheets_client()

    end_date = date.today()
    try:
        exist_df = sheet_to_dataframe(
            sheets_client, spreadsheet_id=sheet_id, sheet_name=sheet_name
        )
        latest_date = pd.to_datetime(exist_df["date"]).max().date()
        start_date = latest_date + timedelta(days=1)
    except NoSuchSheetException:
        logger.warning(f"Sheet {sheet_name} doesn't exist")
        if default_days is None:
            raise ValueError(
                f"Sheet {sheet_name} doesn't exist and --default-days was not provided. "
                "Either create the spreadsheet or pass --default-days and it will be "
                "created for you."
            )
        start_date = end_date - timedelta(days=default_days - 1)

    if start_date > end_date:
        logger.info(f"Data is already synced up to {start_date}")
        return

    logger.info(f"Fetching {data_type} data from {start_date} to {end_date}...")
    if data_type == "sleep":
        new_df = get_sleep_data(fitbit_client, start_date=start_date, end_date=end_date)
    elif data_type == "heart-rate":
        new_df = get_resting_heart_rate(
            fitbit_client, start_date=start_date, end_date=end_date
        )

    # Display summary
    logger.info(f"Retrieved {len(new_df)} new records")

    # Print a preview of the data if in debug mode
    if logger.isEnabledFor(logging.DEBUG):
        pd.set_option("display.max_columns", None)
        logger.debug(f"Data preview:\n{new_df.head()}")

    append_to_sheet(
        sheets_client, new_df, spreadsheet_id=sheet_id, sheet_name=sheet_name
    )
    logger.info(f"Data updated, see updates at {sheets_link(sheet_id)}")


if __name__ == "__main__":
    main()
