import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
from fitbit.api import Fitbit

from health_tracking.auth import run_oauth_flow

# Get Fitbit credentials from environment variables
CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET", "")
TOKEN_PATH = os.environ.get("FITBIT_TOKEN_PATH", "credentials/fitbit_token.json")


def get_fitbit_client() -> Fitbit:
    """Get Fitbit client using authorization code flow with browser-based auth."""

    # Check if we have a token file
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, "r") as token_file:
                token_data = json.load(token_file)
                fitbit = Fitbit(
                    CLIENT_ID,
                    CLIENT_SECRET,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    expires_at=token_data.get("expires_at"),
                    timeout=10,
                )
                # Try refreshing the token if it's expired
                if (
                    fitbit.client.session.token.get("expires_at", 0)
                    < datetime.now().timestamp()
                ):
                    fitbit.client.refresh_token()
                    # Save the refreshed token
                    token_data = {
                        "access_token": fitbit.client.session.token.get("access_token"),
                        "refresh_token": fitbit.client.session.token.get(
                            "refresh_token"
                        ),
                        "expires_at": fitbit.client.session.token.get("expires_at"),
                    }
                    # Make sure the credentials directory exists
                    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
                    with open(TOKEN_PATH, "w") as token_file:
                        json.dump(token_data, token_file)
                return fitbit
        except Exception as e:
            print(f"Error loading token: {e}")
            # Continue with new authorization

    # Check for required credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "Error: FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET environment variables must be set."
        )
        sys.exit(1)

    # Use port 8080 as required by Fitbit app configuration
    port = 8080
    redirect_uri = f"http://localhost:{port}/"

    # Create the OAuth2 client with our local server redirect URI
    fitbit = Fitbit(CLIENT_ID, CLIENT_SECRET, redirect_uri=redirect_uri, timeout=10)

    # Generate authorization URL
    auth_url, _ = fitbit.client.authorize_token_url()

    # Run the OAuth flow
    auth_code = run_oauth_flow(auth_url, port=port)

    # Check if we got the authorization code
    if auth_code is None:
        raise TimeoutError("Error: Timed out waiting for authorization.")

    # Exchange authorization code for tokens
    fitbit.client.fetch_access_token(auth_code)

    # Save the token for future use
    token_data = {
        "access_token": fitbit.client.session.token.get("access_token"),
        "refresh_token": fitbit.client.session.token.get("refresh_token"),
        "expires_at": fitbit.client.session.token.get("expires_at"),
    }

    # Make sure the credentials directory exists
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)

    # Save the token
    with open(TOKEN_PATH, "w") as token_file:
        json.dump(token_data, token_file)
        print(f"Credentials saved to {TOKEN_PATH}")

    return fitbit


def get_sleep_data(
    client: Fitbit,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
) -> pd.DataFrame:
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
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    if start_date is None:
        start_date_dt = datetime.now() - timedelta(days=days)
    else:
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")

    # Initialize empty lists to store data
    all_records: List[Dict[str, Any]] = []

    # Loop through each date in the range
    current_date = start_date_dt
    while current_date <= end_date_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"Fetching sleep data for {date_str}...")

        # Fetch sleep logs data for this date
        sleep_data: Dict[str, Any] = client.sleep(date=date_str)

        # Extract top-level summary data for sleep stages
        top_summary: Dict[str, Any] = sleep_data.get("summary", {})
        top_stages: Dict[str, int] = top_summary.get("stages", {})

        # Process each sleep log
        for sleep in sleep_data.get("sleep", []):
            # Extract basic sleep data
            date = sleep.get("dateOfSleep")
            start_time = sleep.get("startTime")
            end_time = sleep.get("endTime")
            duration_mins = sleep.get("duration") / 60000  # Convert from ms to minutes
            efficiency = sleep.get("efficiency")
            is_main_sleep = sleep.get("isMainSleep")
            minutes_asleep = sleep.get("minutesAsleep")
            minutes_awake = sleep.get("minutesAwake")
            time_in_bed = sleep.get("timeInBed")

            # Create a base record without sleep stages
            record = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "duration_mins": duration_mins,
                "efficiency": efficiency,
                "is_main_sleep": is_main_sleep,
                "minutes_asleep": minutes_asleep,
                "minutes_awake": minutes_awake,
                "time_in_bed": time_in_bed,
            }

            # Add sleep stage data if this is the main sleep and we have top-level summary
            if is_main_sleep and top_stages:
                for stage in ["deep", "light", "rem", "wake"]:
                    record[f"{stage}_minutes"] = top_stages.get(stage, 0)

            all_records.append(record)

        # Move to next day
        current_date += timedelta(days=1)

    # Convert to DataFrame
    df = pd.DataFrame(all_records)

    # Convert date columns to datetime
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["start_time"] = pd.to_datetime(df["start_time"])
        df["end_time"] = pd.to_datetime(df["end_time"])

        # Sort by date and whether it's the main sleep record
        df = df.sort_values(["date", "is_main_sleep"], ascending=[True, False])

    return df


def get_resting_heart_rate(
    client: Fitbit,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
) -> pd.DataFrame:
    """
    Fetch resting heart rate data from Fitbit API and convert to a Pandas DataFrame.

    Args:
        client: Authenticated Fitbit client
        start_date: Start date (YYYY-MM-DD format) for fetching data, defaults to 'days' ago
        end_date: End date (YYYY-MM-DD format) for fetching data, defaults to today
        days: Number of days to fetch if start_date is not specified, defaults to 30

    Returns:
        DataFrame with daily resting heart rate data
    """
    # Set default dates if not provided
    if end_date is None:
        end_date_dt = datetime.now()
    else:
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    if start_date is None:
        start_date_dt = datetime.now() - timedelta(days=days)
    else:
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")

    # Format dates for API
    start_date_str = start_date_dt.strftime("%Y-%m-%d")
    end_date_str = end_date_dt.strftime("%Y-%m-%d")

    print(
        f"Fetching resting heart rate data from {start_date_str} to {end_date_str}..."
    )

    # The Fitbit API endpoint for heart rate time series
    heart_data = client.time_series(
        resource="activities/heart", base_date=start_date_str, end_date=end_date_str
    )

    # Initialize empty list to store the records
    records = []

    # Extract data from response
    for day in heart_data.get("activities-heart", []):
        date = day.get("dateTime")
        value = day.get("value", {})

        # Extract resting heart rate if available
        resting_hr = value.get("restingHeartRate")

        # Only add records that have a resting heart rate value
        if resting_hr is not None:
            records.append({"date": date, "resting_heart_rate": resting_hr})

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Convert date column to datetime
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

    return df
