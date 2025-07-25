import json
import logging
import os
from pathlib import Path
from typing import Annotated, Any, List

import pandas as pd
from google.auth.exceptions import RefreshError
from google.auth.external_account_authorized_user import Credentials as UserCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Set up OAuth 2.0 scopes for Google Sheets access
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Get credentials path from environment variables (optional)
CREDENTIALS_PATH = Path(
    os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials/google.json")
)
TOKEN_PATH = Path(os.environ.get("GOOGLE_TOKEN_PATH", "credentials/google_token.json"))


class NoSuchSheetException(Exception):
    def __init__(self, spreadsheet_id: str, sheet_name: str) -> None:
        super().__init__(
            f"Sheet {sheet_name} does not exist in spreadsheet {spreadsheet_id}"
        )


def sheets_link(spreadsheet_id: str) -> str:
    """Create a link to a Google Sheet"""
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


SheetsClient = Annotated[Any, "Google Sheets API client"]


def get_token_via_oauth(credentials_path: Path) -> Credentials | UserCredentials:
    if not credentials_path.exists():
        raise ValueError(
            f"Error: Google API credentials file not found at {credentials_path}."
            "Please create a project in Google Cloud Console, enable the Sheets API,"
            "and download the OAuth 2.0 credentials to this location."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    return flow.run_local_server(port=0)


def get_sheets_client(credentials_path: Path = CREDENTIALS_PATH) -> SheetsClient:
    """
    Get authenticated Google Sheets client using OAuth 2.0.

    Returns:
        A configured Google Sheets API service resource.
    """

    try:
        with TOKEN_PATH.open("r") as f:
            creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
    except FileNotFoundError:
        creds = get_token_via_oauth(credentials_path)

    # Try to refresh if necessary
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            logger.error("Failed to refresh token: %s", e)

    # If credentials don't exist or are invalid, let the user authorize
    if not creds.valid:
        creds = get_token_via_oauth(credentials_path)

    # Make sure the credentials directory exists
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Save the credentials for future use
    TOKEN_PATH.write_text(creds.to_json())

    # Build and return the sheets service
    return build("sheets", "v4", credentials=creds)


def create_spreadsheet(sheets: SheetsClient, title: str) -> str:
    """
    Create a new Google Sheet with the given title.

    Args:
        sheets: Authenticated Google Sheets client
        title: Title for the spreadsheet

    Returns:
        The spreadsheet ID
    """
    spreadsheet = {"properties": {"title": title}}
    result = sheets.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = result["spreadsheetId"]
    logger.info(f"Created new spreadsheet: {title} (ID: {spreadsheet_id})")
    return spreadsheet_id


def ensure_sheet_exists(
    sheets: SheetsClient, spreadsheet_id: str, sheet_name: str
) -> None:
    """
    Add a new worksheet to an existing spreadsheet.

    Args:
        sheets: Authenticated Google Sheets client
        spreadsheet_id: ID of the target spreadsheet
        sheet_name: Name for the new worksheet
    """
    request = {"addSheet": {"properties": {"title": sheet_name}}}
    # We handle the specific exception for an already existing sheet
    # since this is expected behavior, not a fatal error
    try:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": [request]}
        ).execute()
        logger.info(f"Created new sheet: {sheet_name}")
    except Exception as e:
        if "already exists" in str(e):
            logger.debug(f"Sheet '{sheet_name}' already exists")
        else:
            raise


def dataframe_to_sheet(
    sheets: SheetsClient,
    df: pd.DataFrame,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    include_header: bool = False,
    start_row: int = 1,
) -> None:
    """
    Append rows from a pandas DataFrame to an existing Google Sheet.

    Args:
        sheets: Authenticated Google Sheets client
        df: Pandas DataFrame with rows to append
        spreadsheet_id: ID of the target spreadsheet
        sheet_name: Name of the target worksheet
        include_header: Whether to include column headers
        include_index: Whether to include the DataFrame index
    """
    ensure_sheet_exists(sheets, spreadsheet_id, sheet_name)

    # Convert DataFrame to values list
    values: List[List[Any]] = []
    if include_header:
        values.append(list(df.columns))

    for _, row in df.iterrows():
        values.append(list(row))

    # Update values
    body = json.loads(json.dumps({"values": values}, default=str))

    result = (
        sheets.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A{start_row}",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )

    updates = result.get("updates", {})
    updated_cells = updates.get("updatedCells", 0)
    logger.info(f"{updated_cells} cells appended to {sheet_name}")


def append_to_sheet(
    sheets: SheetsClient,
    df: pd.DataFrame,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    include_header_if_new: bool = True,
) -> None:
    """
    Append rows from a pandas DataFrame to an existing Google Sheet.

    Args:
        sheets: Authenticated Google Sheets client
        df: Pandas DataFrame with rows to append
        spreadsheet_id: ID of the target spreadsheet
        sheet_name: Name of the target worksheet
        include_header: Whether to include column headers
        include_index: Whether to include the DataFrame index
    """
    try:
        # Get the current values to determine where to append
        current_data = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:A")
            .execute()
        )

        current_values = current_data.get("values", [])
        start_row = len(current_values) + 1  # 1-indexed for sheets API
    except HttpError as e:
        # The sheet doesn't exist
        if "Unable to parse range" in e.reason:
            start_row = 1
        else:
            raise

    return dataframe_to_sheet(
        sheets,
        df,
        spreadsheet_id,
        sheet_name,
        include_header=(include_header_if_new and start_row == 1),
        start_row=start_row,
    )


def sheet_to_dataframe(
    sheets: SheetsClient,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    has_header: bool = True,
) -> pd.DataFrame:
    """
    Read a Google Sheet into a pandas DataFrame.

    Args:
        sheets: Authenticated Google Sheets client
        spreadsheet_id: ID of the target spreadsheet
        sheet_name: Name of the target worksheet
        has_header: Whether the first row contains column names

    Returns:
        A pandas DataFrame containing the sheet data
    """
    try:
        result = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=sheet_name)
            .execute()
        )
    except Exception as e:
        if f"Unable to parse range: {sheet_name}" in str(e):
            raise NoSuchSheetException(spreadsheet_id, sheet_name) from e
        raise

    values = result.get("values", [])

    if not values:
        return pd.DataFrame()

    if has_header:
        headers = values[0]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)
    else:
        return pd.DataFrame(values)
