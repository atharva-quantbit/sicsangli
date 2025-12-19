import json
import frappe
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from frappe import _

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SHEET_NAME = "Tender3"
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
        
        # Increased MAX_ROWS to fetch more data
        MAX_ROWS = 1000  # Adjust as needed based on sheet size
        range_name = f"{SHEET_NAME}!A1:Z{MAX_ROWS}"
        logger.info(f"Fetching range: {range_name}")
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        logger.info(f"Raw values fetched: {len(values)} rows")
        
        if not values:
            return {'success': True, 'title_rows': [], 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}
        
        # Title rows from rows 1-3 (indices 0-2), if any
        title_rows = []
        for i in range(min(3, len(values))):
            raw_row = values[i]
            # Determine initial num_cols based on longest row, but we'll adjust later
            padded_row = raw_row + [''] * (26 - len(raw_row)) if len(raw_row) < 26 else raw_row[:26]  # Z is 26 columns
            title_rows.append(padded_row)
        
        # Headers start at row 4 (index 3)
        headers = values[3] if len(values) > 3 else []
        # Trim trailing empty cells in headers
        while headers and not str(headers[-1]).strip():
            headers.pop()
        num_cols = len(headers)
        logger.info(f"Headers identified at row 4: {num_cols} columns")
        
        # Pad title rows to match num_cols
        title_rows = [row[:num_cols] if len(row) >= num_cols else row + [''] * (num_cols - len(row)) for row in title_rows]
        
        # Data rows start from row 5 (index 4)
        data_rows = []
        if len(values) > 4:
            for row in values[4:]:
                padded_row = row[:num_cols] if len(row) >= num_cols else row + [''] * (num_cols - len(row))
                data_rows.append(padded_row)
        
        sheet_json = {
            'success': True,
            'title_rows': title_rows,
            'headers': headers,
            'rows': data_rows,
            'total_rows': len(data_rows),
            'total_columns': num_cols
        }
        logger.info(f"Success: {len(title_rows)} title rows, {len(data_rows)} data rows, {num_cols} columns (starting from row 4)")
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