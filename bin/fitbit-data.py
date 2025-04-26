#!/usr/bin/env python3

import argparse
import sys
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, "src")
from health_tracking.fitbit import (
    get_fitbit_client,
    get_resting_heart_rate,
    get_sleep_data,
)


def main() -> None:
    """Command-line interface to fetch and save Fitbit data."""
    parser = argparse.ArgumentParser(description="Fetch Fitbit data")

    # Data type argument
    parser.add_argument(
        "--type",
        type=str,
        choices=["sleep", "heart-rate"],
        default="sleep",
        help="Type of data to fetch (sleep or heart-rate)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of data to fetch (default: 30)",
    )
    parser.add_argument("--csv-out", type=str, help="Path to save CSV output file")
    args = parser.parse_args()

    # Get authenticated client
    client = get_fitbit_client()

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days - 1)
    if args.type == "sleep":
        # Fetch sleep data
        print(f"Fetching sleep data for the past {args.days} days...")
        data_df = get_sleep_data(client, start_date=start_date, end_date=end_date)

        # Display summary
        print(f"\nRetrieved {len(data_df)} sleep records")

    elif args.type == "heart-rate":
        # Fetch resting heart rate data
        print(f"Fetching resting heart rate data for the past {args.days} days...")
        data_df = get_resting_heart_rate(
            client, start_date=start_date, end_date=end_date
        )

        # Display summary
        print(f"\nRetrieved {len(data_df)} heart rate records")

    # Show date range for either data type
    if not data_df.empty:
        print(
            f"Date range: {data_df['date'].min().date()} to {data_df['date'].max().date()}"
        )

    # Save to CSV if requested
    if args.csv_out:
        data_df.to_csv(args.csv_out, index=False)
        print(f"Data saved to {args.csv_out}")
    else:
        # Print a preview of the data
        pd.set_option("display.max_columns", None)
        print("\nData preview:")
        print(data_df.head())


if __name__ == "__main__":
    main()
