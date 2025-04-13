import os
import sys
import json
from typing import List, Optional, Any, Dict, cast
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource

# Set up OAuth 2.0 scopes for Google Sheets access
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Get credentials path from environment variables (optional)
CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json"
)
TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "credentials/token.json")


def get_sheets_client() -> Resource:
    """
    Get authenticated Google Sheets client using OAuth 2.0.

    Returns:
        A configured Google Sheets API service resource.
    """
    creds = None

    # Check if we have a token file
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r") as token_file:
            creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)

    # If credentials don't exist or are invalid, let the user authorize
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check for credentials file
            if not os.path.exists(CREDENTIALS_PATH):
                print(
                    f"Error: Google API credentials file not found at {CREDENTIALS_PATH}."
                )
                print(
                    "Please create a project in Google Cloud Console, enable the Sheets API,"
                )
                print("and download the OAuth 2.0 credentials to this location.")
                sys.exit(1)

            # Start the OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Make sure the credentials directory exists
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)

        # Save the credentials for future use
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
            print(f"Credentials saved to {TOKEN_PATH}")

    # Build and return the sheets service
    return build("sheets", "v4", credentials=creds)


def create_spreadsheet(sheets: Resource, title: str) -> str:
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
    print(f"Created new spreadsheet: {title} (ID: {spreadsheet_id})")
    return spreadsheet_id


def create_sheet(sheets: Resource, spreadsheet_id: str, sheet_name: str) -> None:
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
        print(f"Created new sheet: {sheet_name}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Sheet '{sheet_name}' already exists")
        else:
            raise


def dataframe_to_sheet(
    sheets: Resource,
    df: pd.DataFrame,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    clear_sheet: bool = True,
) -> None:
    """
    Write a pandas DataFrame to a Google Sheet.

    Args:
        sheets: Authenticated Google Sheets client
        df: Pandas DataFrame to write
        spreadsheet_id: ID of the target spreadsheet
        sheet_name: Name of the target worksheet
        include_index: Whether to include the DataFrame index
        clear_sheet: Whether to clear existing data in the sheet
    """
    # Check if sheet exists, create it if not
    sheet_metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets_list = sheet_metadata.get("sheets", [])
    sheet_exists = False

    for sheet in sheets_list:
        if sheet["properties"]["title"] == sheet_name:
            sheet_exists = True
            break

    if not sheet_exists:
        create_sheet(sheets, spreadsheet_id, sheet_name)

    # Clear the sheet if requested
    if clear_sheet:
        sheets.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=sheet_name
        ).execute()

    # Convert DataFrame to values list
    values: List[List[Any]] = []

    # Add headers and data - simplified approach that typechecks
    headers: List[Any] = []
    for col in df.columns:
        headers.append(col)
    values.append(headers)

    for _, row in df.iterrows():
        row_list: List[Any] = []
        for val in row:
            row_list.append(val)
        values.append(row_list)

    # Update values
    body = {"values": values}

    result = (
        sheets.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body=body,
        )
        .execute()
    )

    print(f"{result.get('updatedCells')} cells updated in {sheet_name}")


def append_to_sheet(
    sheets: Resource,
    df: pd.DataFrame,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    include_header: bool = False,
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
    # Check if sheet exists, create it if not
    sheet_metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets_list = sheet_metadata.get("sheets", [])
    sheet_exists = False

    for sheet in sheets_list:
        if sheet["properties"]["title"] == sheet_name:
            sheet_exists = True
            break

    if not sheet_exists:
        create_sheet(sheets, spreadsheet_id, sheet_name)

    # Get the current values to determine where to append
    current_data = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:A")
        .execute()
    )

    current_values = current_data.get("values", [])
    start_row = len(current_values) + 1  # 1-indexed for sheets API

    # Convert DataFrame to values list - simplified approach
    values: List[List[Any]] = []

    # Add headers if requested and sheet is empty
    if include_header and start_row == 1:
        headers: List[Any] = []
        for col in df.columns:
            headers.append(col)
        values.append(headers)

    # Add data rows - simplified approach
    for _, row in df.iterrows():
        row_list: List[Any] = []
        for val in row:
            row_list.append(val)
        values.append(row_list)

    # Append values
    body: Dict[str, List[List[Any]]] = {"values": values}

    result = (
        sheets.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A{start_row}",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )

    updates = result.get("updates", {})
    updated_cells = updates.get("updatedCells", 0)
    print(f"{updated_cells} cells appended to {sheet_name}")


def sheet_to_dataframe(
    sheets: Resource,
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
    result = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
    )

    values = result.get("values", [])

    if not values:
        return pd.DataFrame()

    if has_header:
        headers = values[0]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)
    else:
        return pd.DataFrame(values)


def main() -> None:
    """Command-line interface to demonstrate Google Sheets integration."""
    import argparse

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
