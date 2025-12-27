import frappe
import logging
from functools import lru_cache
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SHEET_NAME = "Tender3"
SERVICE_ACCOUNT_FILE = "/home/erpadmin/webpage-bench/sites/credentials/google_sheets.json"


SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)

MAX_COLS = 26      # A-Z
HEADER_ROW_INDEX = 3  # Row 4
DATA_START_INDEX = 4  # Row 5
TITLE_ROWS_COUNT = 3
MAX_ROWS = 1000

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_sheets_service():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def pad_or_trim(row, length):
    row = row or []
    return row[:length] if len(row) >= length else row + [''] * (length - len(row))


def fetch_sheet_data():
    try:
        service = get_sheets_service()

        range_name = f"{SHEET_NAME}!A1:Z{MAX_ROWS}"
        logger.info(f"Fetching sheet range: {range_name}")

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING"
        ).execute()

        values = result.get("values", [])
        if not values:
            return {
                "success": True,
                "title_rows": [],
                "headers": [],
                "rows": [],
                "total_rows": 0,
                "total_columns": 0
            }

        # -------- Title Rows --------
        title_rows = [
            pad_or_trim(values[i], MAX_COLS)
            for i in range(min(TITLE_ROWS_COUNT, len(values)))
        ]

        # -------- Headers --------
        headers = values[HEADER_ROW_INDEX] if len(values) > HEADER_ROW_INDEX else []
        headers = [h for h in headers if str(h).strip()]
        num_cols = len(headers)

        if num_cols == 0:
            return {"success": False, "error": "Header row is empty"}

        title_rows = [pad_or_trim(row, num_cols) for row in title_rows]

        # -------- Data Rows --------
        data_rows = []
        for row in values[DATA_START_INDEX:]:
            if any(str(cell).strip() for cell in row):
                data_rows.append(pad_or_trim(row, num_cols))

        return {
            "success": True,
            "title_rows": title_rows,
            "headers": headers,
            "rows": data_rows,
            "total_rows": len(data_rows),
            "total_columns": num_cols
        }

    except Exception as e:
        logger.exception("Error fetching sheet data")
        return {"success": False, "error": str(e)}


# ---------- Frappe API ----------
@frappe.whitelist(allow_guest=True)
def get_tender_json():
    data = fetch_sheet_data()

    frappe.response["data"] = data
    frappe.response["type"] = "json"
    frappe.response["http_status_code"] = 200
    frappe.local.response.headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    }

    return data
