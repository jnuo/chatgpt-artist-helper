import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
load_dotenv()

# Set the scope for reading/writing Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Path to your service account key file (you need to provide this JSON file)
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# The ID of your Google Sheet
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def get_sheet_data(sheet_name: str):
    """
    Reads all data from the specified sheet in the Google Spreadsheet.
    :param sheet_name: Name of the worksheet/tab to read from.
    :return: List of rows (each row is a list of cell values)
    """
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    return sheet.get_all_values()
