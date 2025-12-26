import json
import frappe
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from frappe import _

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SERVICE_ACCOUNT_FILE = "/home/erpadmin/webpage-bench/apps/sicsangli/sicsangli/public/js/api_tokens.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_sheet_data(sheet_name, max_rows=100, max_cols=26, header_row_idx=None):
    """
    Unified function to fetch sheet data.
    - If header_row_idx is None, dynamically find the first non-empty row as headers.
    - Otherwise, use the specified row index (0-based) for headers.
    """
    try:
        logger.info(f"Starting fetch_sheet_data for sheet: {sheet_name}")
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        logger.info("Google Sheets service built.")

        range_name = f"{sheet_name}!A1:Z{max_rows}"
        logger.info(f"Fetching range: {range_name}")
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        values = result.get('values', [])
        logger.info(f"Raw values fetched: {len(values)} rows")

        if not values:
            return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}

        # Pad rows to max_cols if needed
        for row in values:
            if len(row) < max_cols:
                row.extend([''] * (max_cols - len(row)))

        # Determine header row
        if header_row_idx is None:
            # Dynamic: Find first non-empty row
            header_row_idx = next((i for i, row in enumerate(values) if any(cell.strip() for cell in row)), None)
            if header_row_idx is None:
                return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}
        else:
            # Fixed index, ensure it exists (handle if passed as str 'null')
            if isinstance(header_row_idx, str) and header_row_idx.lower() == 'null':
                header_row_idx = None
                # Re-run dynamic logic
                header_row_idx = next((i for i, row in enumerate(values) if any(cell.strip() for cell in row)), None)
                if header_row_idx is None:
                    return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}
            else:
                # Convert to int if str
                if isinstance(header_row_idx, str):
                    header_row_idx = int(header_row_idx)
                if header_row_idx >= len(values):
                    return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}

        # Extract headers and trim trailing empty cells
        headers = values[header_row_idx]
        headers = [cell.strip() if cell else '' for cell in headers]  # Clean headers
        while headers and not headers[-1]:
            headers.pop()
        num_cols = len(headers)

        # Extract data rows after header row, skipping fully empty rows
        start_data_idx = header_row_idx + 1
        data_rows = []
        for row_idx in range(start_data_idx, len(values)):
            row = values[row_idx]
            # Pad if needed
            if len(row) < num_cols:
                row = row + [''] * (num_cols - len(row))
            # Check if row has any non-empty cell in first num_cols
            if any(cell.strip() for cell in row[:num_cols]):
                data_rows.append(row[:num_cols])  # Trim to num_cols

        sheet_json = {
            'success': True,
            'headers': headers,
            'rows': data_rows,
            'total_rows': len(data_rows),
            'total_columns': num_cols
        }
        logger.info(f"Success for {sheet_name}: {len(data_rows)} filtered rows, {num_cols} columns")
        return sheet_json

    except Exception as e:
        logger.error(f"fetch_sheet_data failed for {sheet_name}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def get_tender_json(sheet_name="Tender", header_row_idx=None, max_rows=50, max_cols=26):
    """
    Unified whitelisted method to fetch tender JSON.
    Parameters:
    - sheet_name: Name of the sheet (default: "Tender")
    - header_row_idx: Fixed header row index (0-based), or None for dynamic (default: None)
    - max_rows: Maximum rows to fetch (default: 50)
    - max_cols: Maximum columns to pad (default: 26)
    
    Examples:
    - For "Tender": header_row_idx=0
    - For "Tender2": header_row_idx=2
    - For "Sheet_pdf": header_row_idx=None (dynamic)
    """
    try:
        # Handle string 'null' as None
        if header_row_idx == 'null':
            header_row_idx = None

        # Set defaults based on sheet_name if not provided
        if sheet_name == "Tender":
            if header_row_idx is None:
                header_row_idx = 0
            max_rows = 50
        elif sheet_name == "Tender2":
            if header_row_idx is None:
                header_row_idx = 2
            max_rows = 50
        elif sheet_name == "Sheet_pdf":
            if header_row_idx is None:
                header_row_idx = None  # Dynamic
            max_rows = 100
        else:
            max_rows = max_rows or 100

        # Ensure max_rows and max_cols are ints
        max_rows = int(max_rows)
        max_cols = int(max_cols)

        data = fetch_sheet_data(sheet_name, max_rows, max_cols, header_row_idx)
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
        logger.error(f"get_tender_json error for {sheet_name}: {str(e)}", exc_info=True)
        error_response = {'success': False, 'error': str(e)}
        frappe.response['data'] = error_response
        frappe.response['type'] = 'json'
        frappe.response['http_status_code'] = 200  # Never 500
        return error_response