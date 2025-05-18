import json
import logging
import os
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import pandas as pd
from fitbit.api import Fitbit

from health_tracking.auth import run_oauth_flow

logger = logging.getLogger(__name__)

# Get Fitbit credentials from environment variables
CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET")
TOKEN_PATH = Path(os.environ.get("FITBIT_TOKEN_PATH", "credentials/fitbit_token.json"))
REDIRECT_URI = "http://localhost:8080/"
Fitbit.API_VERSION = 1.2


class Tokens(TypedDict):
    access_token: str
    refresh_token: str
    expires_at: float


class TokenStore:
    def __init__(self, token_path: Path = TOKEN_PATH) -> None:
        self.token_path = token_path

    def read(self) -> Optional[Tokens]:
        try:
            with self.token_path.open("r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def write(self, tokens: Tokens) -> None:
        # Make sure the credentials directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        with self.token_path.open("w") as f:
            json.dump(tokens, f)


def get_fitbit_client(
    client_id: Optional[str] = CLIENT_ID,
    client_secret: Optional[str] = CLIENT_SECRET,
    redirect_uri: str = REDIRECT_URI,
    token_path: Path = TOKEN_PATH,
) -> Fitbit:
    """Get Fitbit client using authorization code flow with browser-based auth."""

    # Check for required credentials
    if not client_id or not client_secret:
        raise ValueError(
            "Error: FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET environment variables must be set."
        )

    token_store = TokenStore(token_path)

    try:
        tokens = token_store.read()
        if tokens is not None:
            return Fitbit(
                client_id,
                client_secret,
                tokens["access_token"],
                tokens["refresh_token"],
                tokens["expires_at"],
            )
    except Exception as e:
        logger.warning(f"Error loading token: {e}")
        # Continue with new authorization

    # Create the OAuth2 client and run a local server to handle the redirect flow
    fitbit = Fitbit(CLIENT_ID, CLIENT_SECRET, redirect_uri=redirect_uri, timeout=10)
    auth_url, _ = fitbit.client.authorize_token_url()
    auth_port = urllib.parse.urlparse(redirect_uri).port
    if auth_port is None:
        auth_port = 80
    auth_code = run_oauth_flow(auth_url, port=auth_port)
    if auth_code is None:
        raise TimeoutError("Error: Timed out waiting for authorization.")

    # Exchange authorization code for tokens
    fitbit.client.fetch_access_token(auth_code)

    # Save the token for future use
    tokens = Tokens(
        access_token=fitbit.client.session.token.get("access_token"),
        refresh_token=fitbit.client.session.token.get("refresh_token"),
        expires_at=fitbit.client.session.token.get("expires_at"),
    )
    token_store.write(tokens)

    return fitbit


def get_sleep_data(
    client: Fitbit,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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
        end_date = date.today()
    if start_date is None:
        start_date = end_date

    # Format dates for API
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    logger.info(f"Fetching sleep data from {start_date_str} to {end_date_str}...")

    # Fetch sleep logs for date range in one API call
    sleep_range_data = client.time_series(
        resource="sleep",
        base_date=start_date_str,
        end_date=end_date_str,
    )

    # Initialize empty lists to store data
    all_records: List[Dict[str, Any]] = []

    # Process each sleep log in the response
    for sleep in sleep_range_data.get("sleep", []):
        # Extract basic sleep data
        date_of_sleep = sleep.get("dateOfSleep")
        start_time = sleep.get("startTime")
        end_time = sleep.get("endTime")
        duration_mins = (
            # Convert from ms to minutes
            sleep.get("duration") / 60000 if sleep.get("duration") else 0
        )
        efficiency = sleep.get("efficiency")
        is_main_sleep = sleep.get("isMainSleep")
        minutes_asleep = sleep.get("minutesAsleep")
        minutes_awake = sleep.get("minutesAwake")
        time_in_bed = sleep.get("timeInBed")

        # Extract sleep stages if available
        stages = {}
        levels = sleep.get("levels", {})
        summary = levels.get("summary", {})

        for stage in ["deep", "light", "rem", "wake"]:
            stage_data = summary.get(stage, {})
            if isinstance(stage_data, dict):
                stages[f"{stage}_minutes"] = stage_data.get("minutes", 0)

        # Create a record with all available data
        record = {
            "date": date_of_sleep,
            "start_time": start_time,
            "end_time": end_time,
            "duration_mins": duration_mins,
            "efficiency": efficiency,
            "is_main_sleep": is_main_sleep,
            "minutes_asleep": minutes_asleep,
            "minutes_awake": minutes_awake,
            "time_in_bed": time_in_bed,
            **stages,
        }

        all_records.append(record)

    # Convert to DataFrame
    df = pd.DataFrame(all_records)

    # Convert date columns to datetime
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["start_time"] = pd.to_datetime(df["start_time"])
        df["end_time"] = pd.to_datetime(df["end_time"])

        # Sort by date and whether it's the main sleep record
        df = df.sort_values(["date", "is_main_sleep"], ascending=[True, False])

    return df


def get_resting_heart_rate(
    client: Fitbit,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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
        end_date = date.today()
    if start_date is None:
        start_date = end_date

    # Format dates for API
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    logger.info(
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
        date_of_sleep = day.get("dateTime")
        value = day.get("value", {})

        # Extract resting heart rate if available
        resting_hr = value.get("restingHeartRate")

        # Only add records that have a resting heart rate value
        if resting_hr is not None:
            records.append({"date": date_of_sleep, "resting_heart_rate": resting_hr})

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Convert date column to date
    if not df.empty:
        # First convert to datetime, then extract just the date part
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.sort_values("date")

    return df
