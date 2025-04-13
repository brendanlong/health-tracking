import os
import sys
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import pandas as pd
from fitbit.api import Fitbit

# Get Fitbit credentials from environment variables
CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080/"


def get_fitbit_client() -> Fitbit:
    """Get Fitbit tokens using authorization code flow with manual copy-paste."""

    # Check for required credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "Error: FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET environment variables must be set."
        )
        sys.exit(1)

    # Create the OAuth2 client
    fitbit = Fitbit(CLIENT_ID, CLIENT_SECRET, timeout=10)

    # Generate authorization URL
    auth_url, _ = fitbit.client.authorize_token_url()

    # Instruct user to authorize the app
    print("\n1. Go to this URL in your browser:")
    print(f"\n{auth_url}\n")
    print("2. Authorize the app and you'll be redirected to a URL.")
    print("3. Copy that URL and paste it below, even if it shows an error page.\n")

    # Get the redirect URL from user
    redirect_url = input("Paste the redirect URL here: ")

    # Parse the authorization code from the redirect URL
    parsed_url = urlparse(redirect_url)
    code = parse_qs(parsed_url.query).get("code", [None])[0]

    if not code:
        print("Error: No authorization code found in the URL.")
        sys.exit(1)

    # Exchange authorization code for tokens
    fitbit.client.fetch_access_token(code)

    return fitbit


def get_sleep_data(client: Fitbit, start_date=None, end_date=None, days=30) -> pd.DataFrame:
    """
    Fetch sleep data from Fitbit API and convert to a Pandas DataFrame.
    
    Args:
        client: Authenticated Fitbit client
        start_date: Start date (YYYY-MM-DD format) for fetching data, defaults to 'days' ago
        end_date: End date (YYYY-MM-DD format) for fetching data, defaults to today
        days: Number of days to fetch if start_date is not specified, defaults to 30
        
    Returns:
        DataFrame with sleep data including date, start/end times, and sleep stages
    """
    # Set default dates if not provided
    if end_date is None:
        end_date_dt = datetime.now()
    else:
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    if start_date is None:
        start_date_dt = datetime.now() - timedelta(days=days)    
    else:
        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    # Initialize empty lists to store data
    all_records = []
    
    # Loop through each date in the range
    current_date = start_date_dt
    while current_date <= end_date_dt:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Fetching sleep data for {date_str}...")
        
        # Fetch sleep logs data for this date
        sleep_data = client.sleep(date=date_str)
        
        # Extract top-level summary data for sleep stages
        top_summary = sleep_data.get('summary', {})
        top_stages = top_summary.get('stages', {})
        
        # Process each sleep log
        for sleep in sleep_data.get('sleep', []):
            # Extract basic sleep data
            date = sleep.get('dateOfSleep')
            start_time = sleep.get('startTime')
            end_time = sleep.get('endTime')
            duration_mins = sleep.get('duration') / 60000  # Convert from ms to minutes
            efficiency = sleep.get('efficiency')
            is_main_sleep = sleep.get('isMainSleep')
            minutes_asleep = sleep.get('minutesAsleep')
            minutes_awake = sleep.get('minutesAwake')
            time_in_bed = sleep.get('timeInBed')
            
            # Create a base record without sleep stages
            record = {
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'duration_mins': duration_mins,
                'efficiency': efficiency,
                'is_main_sleep': is_main_sleep,
                'minutes_asleep': minutes_asleep,
                'minutes_awake': minutes_awake,
                'time_in_bed': time_in_bed,
            }
            
            # Add sleep stage data if this is the main sleep and we have top-level summary
            if is_main_sleep and top_stages:
                for stage in ['deep', 'light', 'rem', 'wake']:
                    record[f'{stage}_minutes'] = top_stages.get(stage, 0)
            
            all_records.append(record)

        # Move to next day
        current_date += timedelta(days=1)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Convert date columns to datetime
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['start_time'] = pd.to_datetime(df['start_time'])
        df['end_time'] = pd.to_datetime(df['end_time'])
        
        # Sort by date and whether it's the main sleep record
        df = df.sort_values(['date', 'is_main_sleep'], ascending=[True, False])
    
    return df


def main():
    """Command-line interface to fetch and save Fitbit sleep data."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch Fitbit sleep data")
    parser.add_argument("--days", type=int, default=30, help="Number of days of data to fetch (default: 30)")
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
        print(f"Date range: {sleep_df['date'].min().date()} to {sleep_df['date'].max().date()}")
    
    # Save to CSV if requested
    if args.csv_out:
        sleep_df.to_csv(args.csv_out, index=False)
        print(f"Sleep data saved to {args.csv_out}")
    else:
        # Print a preview of the data
        pd.set_option('display.max_columns', None)
        print("\nData preview:")
        print(sleep_df.head())


if __name__ == "__main__":
    main()
