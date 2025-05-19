## Project Overview
Health Tracking is a Python tool that extracts personal health data from Fitbit and uploads it to Google Sheets for analysis and visualization.

## Key Files and Components
- `README.md`: The general README for this project
- `src/health_tracking/fitbit.py`: Fitbit API client with authentication and data fetching
- `src/health_tracking/sheets.py`: Google Sheets API client and data management
- `src/health_tracking/auth.py`: OAuth authentication infrastructure with browser-based flow
- `bin/fitbit-data.py`: CLI tool to fetch Fitbit data and export to CSV
- `bin/sheets-upload.py`: CLI tool to upload data to Google Sheets
- `bin/fitbit-sheets-sync.py`: Direct sync from Fitbit to Google Sheets

## Development Guidelines
- Type checking: Use pyright in strict mode (`typeCheckingMode = "strict"` in pyproject.toml)
- Formatting: Use ruff (similar to black) for code formatting
- Use pandas for data manipulation and DataFrame-based processing
- Error handling: Handle errors at the appropriate level, avoid catching exceptions broadly
- Avoid comments that just say what the code is doing
- Use uv as the package manager
- Don't add code we don't need
- Clean up code whenever it's unused
- Don't comment about why we added code unless it's necessary for future context

## Project Structure
- `bin/`: CLI executables
- `src/health_tracking/`: Core package modules
- `credentials/`: API tokens (gitignored)
- `deploy/`: AWS Lambda deployment resources