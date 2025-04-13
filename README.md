# Setting Up API Access

## Register a Fitbit Developer App

1. Go to Fitbit Developer
2. Create a new app with:
    * Application Name: "Personal Health Tracker" (or your preferred name)
    * Description: "Personal app to export my own health data"
    * Application Website: You can use "http://localhost:8080/"
    * Organization: Your name
    * OAuth 2.0 Application Type: "Personal"
    * Callback URL: "http://localhost:8080/"
    * Default Access Type: "Read-Only"
3. After creating the app, you'll receive a Client ID - copy this into the script

## Set Up Google Sheets API

1. Go to Google Cloud Console
2. Create a new project
3. Enable the Google Sheets API
4. Create credentials (Service Account key)
5. Download the JSON credentials file and save it as google_sheets_credentials.json in the same directory as the script

## Install Required Python Packages

```bash
pip install requests oauthlib requests_oauthlib gspread google-auth
```

# How the Script Works

1. Authenticates with Fitbit: Uses OAuth 2.0 to connect to your Fitbit account
2. Creates a Google Sheet: Sets up a spreadsheet with separate sheets for each data type
3. Fetches Fitbit Data: Gets your HRV, resting heart rate, skin temperature, sleep metrics, and activity data
4. Updates Google Sheets: Adds the fetched data to the appropriate sheets

# Running the Script

When you run the script:

1. It will generate an authorization URL - open this in your browser
2. Log in to your Fitbit account and authorize the app
3. Copy the URL you're redirected to (even if it shows an error page)
4. Paste this URL back into the script
5. The script will then fetch your data and add it to Google Sheets
