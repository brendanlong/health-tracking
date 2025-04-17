#!/usr/bin/env python3

import sys
import argparse
import pandas as pd

sys.path.insert(0, "src")
from health_tracking.fitbit import get_fitbit_client, get_sleep_data


def main() -> None:
    """Command-line interface to fetch and save Fitbit sleep data."""
    parser = argparse.ArgumentParser(description="Fetch Fitbit sleep data")
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

    # Fetch sleep data
    print(f"Fetching sleep data for the past {args.days} days...")
    sleep_df = get_sleep_data(client, days=args.days)

    # Display summary
    print(f"\nRetrieved {len(sleep_df)} sleep records")
    if not sleep_df.empty:
        print(
            f"Date range: {sleep_df['date'].min().date()} to {sleep_df['date'].max().date()}"
        )

    # Save to CSV if requested
    if args.csv_out:
        sleep_df.to_csv(args.csv_out, index=False)
        print(f"Sleep data saved to {args.csv_out}")
    else:
        # Print a preview of the data
        pd.set_option("display.max_columns", None)
        print("\nData preview:")
        print(sleep_df.head())


if __name__ == "__main__":
    main()
