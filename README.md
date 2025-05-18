# Health Tracking

A Python-based tool to export health data from fitness trackers to Google Sheets for personal analysis and visualization.

## Setting Up API Access

### Register a Fitbit Developer App

1. Go to [Fitbit Developer](https://dev.fitbit.com/apps/new)
2. Create a new app with:
   * Application Name: "Personal Health Tracker" (or your preferred name)
   * Description: "Personal app to export my own health data"
   * Application Website: You can use "http://localhost:8080/"
   * Organization: Your name
   * OAuth 2.0 Application Type: "Personal"
   * Callback URL: "http://localhost:8080/"
   * Default Access Type: "Read-Only"
3. After creating the app, you'll receive a Client ID and Client Secret
4. Set these as environment variables:
   ```bash
   export FITBIT_CLIENT_ID="your_client_id"
   export FITBIT_CLIENT_SECRET="your_client_secret"
   ```

### Set Up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Sheets API
4. Go to "APIs & Services" > "Credentials"
5. Click "Create Credentials" > "OAuth client ID"
6. Set Application Type to "Desktop app" and give it a name
7. Download the JSON credentials file
8. Create a directory named `credentials` and place the file inside
9. For first-time use, set the credentials path:
   ```bash
   export GOOGLE_CREDENTIALS_PATH="credentials/your_downloaded_file.json"
   ```

## Installation

Clone the repository and set up the environment using [uv](https://github.com/astral-sh/uv):

```bash
git clone <repository-url>
cd health-tracking
./setup.sh
source venv/bin/activate
```

## Available Tools

### Fitbit Data Export

Extract sleep data from your Fitbit account:

```bash
./bin/fitbit-data --days 30 --csv-out sleep_data.csv
```

Options:
- `--days`: Number of days of data to fetch (default: 30)
- `--csv-out`: Path to save the CSV output file

### Google Sheets Integration

The `./bin/sheets-upload` script provides several ways to work with Google Sheets:

#### Create a new spreadsheet and upload data

```bash
./bin/sheets-upload --create "My Health Data" --csv-to-sheet sleep_data.csv
```

This creates a new spreadsheet and saves the spreadsheet ID in the console output, which you should save for future use.

#### Append new data to an existing spreadsheet

```bash
./bin/sheets-upload --spreadsheet-id "your_spreadsheet_id" --append-csv new_data.csv
```

#### Create a new worksheet in an existing spreadsheet

```bash
./bin/sheets-upload --spreadsheet-id "your_spreadsheet_id" --sheet-name "New Sheet" --create-sheet
```

#### Upload data to a specific worksheet

```bash
./bin/sheets-upload --spreadsheet-id "your_spreadsheet_id" --sheet-name "Sheet Name" --csv-to-sheet data.csv
```

## Authentication Flow

### Fitbit Authentication

When you run the Fitbit script for the first time:

1. It will generate an authorization URL - open this in your browser
2. Log in to your Fitbit account and authorize the app
3. Copy the URL you're redirected to (even if it shows an error page)
4. Paste this URL back into the script
5. The script will fetch your data and save it to the specified output

### Google Sheets Authentication

When you run the Google Sheets script for the first time:

1. A browser window will open automatically
2. Sign in with your Google account and authorize the app
3. The authentication token will be saved locally for future use
4. You only need to authenticate once unless you revoke access or delete the token file

## Adding More Data Sources

Support for additional fitness trackers and health data sources is planned for future releases.

## Project Structure

```
health-tracking/
├── bin/                     # Executable scripts
├── credentials/             # API credentials (gitignored)
├── src/                     # Source code
│   └── health_tracking/     # Main package
│       ├── __init__.py      # Package metadata
│       ├── auth.py          # OAuth authentication
│       ├── fitbit.py        # Fitbit API interaction
│       └── sheets.py        # Google Sheets integration
├── pyproject.toml           # Package configuration and dependency management
└── setup.sh                 # Environment setup script using uv
```