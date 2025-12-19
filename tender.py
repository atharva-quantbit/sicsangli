import json
import frappe
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from frappe import _

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SHEET_NAME = "Tender"
SERVICE_ACCOUNT_FILE = "/home/erpadmin/webpage-bench/apps/sicsangli/sicsangli/public/js/credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_sheet_data():
    try:
        logger.info("Starting fetch_sheet_data: Loading credentials...")
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        logger.info("Google Sheets service built.")

        MAX_ROWS = 50
        range_name = f"{SHEET_NAME}!A1:Z{MAX_ROWS}"
        logger.info(f"Fetching range: {range_name}")

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()

        values = result.get('values', [])
        logger.info(f"Raw values fetched: {len(values)} rows")

        # Pad to 26 columns
        MAX_COLS = 26
        for row in values:
            row.extend([''] * (MAX_COLS - len(row)))

        # Pad to 50 rows
        while len(values) < MAX_ROWS:
            values.append([''] * MAX_COLS)

        headers = values[0] if values else [''] * MAX_COLS
        raw_data_rows = values[1:] if len(values) > 1 else []
        data_rows = [row for row in raw_data_rows if any(cell.strip() for cell in row)]

        sheet_json = {
            'success': True,
            'headers': headers,
            'rows': data_rows,
            'total_rows': len(data_rows),
            'total_columns': len(headers)
        }
        logger.info(f"Success: {len(data_rows)} filtered rows, {len(headers)} columns")
        return sheet_json

    except Exception as e:
        logger.error(f"fetch_sheet_data failed: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


@frappe.whitelist(allow_guest=True)
def get_tender_json():
    """
    Returns RAW JSON with correct headers.
    Fixes 417, 500, and UI error display.
    """
    try:
        data = fetch_sheet_data()

        # FORCE RAW JSON RESPONSE
        frappe.response['data'] = data
        frappe.response['type'] = 'json'  # Critical!
        frappe.response['http_status_code'] = 200

        # Optional: Set headers to prevent 417
        frappe.local.response.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
        }

        return data  # This will be serialized safely

    except Exception as e:
        logger.error(f"get_tender_json error: {str(e)}", exc_info=True)
        error_response = {'success': False, 'error': str(e)}
        
        frappe.response['data'] = error_response
        frappe.response['type'] = 'json'
        frappe.response['http_status_code'] = 200  # Never 500

        return error_response