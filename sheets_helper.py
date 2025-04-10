from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def fetch_event_data():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SPREADSHEET_ID = '1psKgP-Mqjn3XKyTntEUYD040OQmrRiTsS50j0b0FNkg'
    RANGE_NAME = 'Sheet1!A1:D'

    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()

    return result.get('values', [])


