
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= CONFIG =================
SUPPLIERS_SHEET_ID = "1lmujebRWI16hlpbcAqoAvQSXFJexWvXbtBhLk5Xc3Jo"
SOURCE1_ID = "1i5dcNxLT-E3HSoqwad8O4yccq8HheffW"
SOURCE2_ID = "1kssoLVWuN-6Y8PV9Fd_xBgcqQfrwSbvUi5OLzpe2kXg"

SUPPLIERS_TAB = "Sheet1"
SOURCE1_TAB = "LIVE & CLUB"
SOURCE2_TAB = "Sales"

# ================= AUTH =================
scopes = ["https://www.googleapis.com/auth/spreadsheets"]

import json
import os
import gspread
from google.oauth2.service_account import Credentials

creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

gc = gspread.authorize(creds)

gc = gspread.authorize(creds)

suppliers = gc.open_by_key(SUPPLIERS_SHEET_ID).worksheet(SUPPLIERS_TAB)
source1 = gc.open_by_key(SOURCE1_ID).worksheet(SOURCE1_TAB)
source2 = gc.open_by_key(SOURCE2_ID).worksheet(SOURCE2_TAB)

# ================= DATE NORMALISER (IGNORE TIME) =================
def normalize_date(value):
    if not value:
        return None

    # Google Sheets sometimes sends datetime strings
    value = str(value).strip()

    # Try parsing full datetime first (ignore time part)
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except:
            continue

    return None

# ================= LOAD DATA =================
headers = suppliers.row_values(1)
row28_flags = suppliers.row_values(28)

source1_data = source1.get_all_values()
source2_data = source2.get_all_values()

# ================= BUILD LOOKUPS =================
source1_lookup = {}
for i, row in enumerate(source1_data):
    if len(row) < 2:
        continue
    d = normalize_date(row[1])  # Column B
    if d:
        source1_lookup[d] = row

source2_lookup = {}
for i, row in enumerate(source2_data):
    if len(row) < 10:
        continue
    d = normalize_date(row[9])  # Column J
    if d:
        source2_lookup[d] = row

# ================= BATCH UPDATES =================
updates = []

# ================= MAIN LOOP =================
for col_index, header in enumerate(headers, start=1):

    # 🚫 LEAVE OVERRIDE (ROW 28)
    if col_index <= len(row28_flags):
        if str(row28_flags[col_index - 1]).strip().upper() == "LEAVE":
            continue

    match_date = normalize_date(header)
    if not match_date:
        continue

    col_letter = gspread.utils.rowcol_to_a1(1, col_index)[:-1]

    # ================= SOURCE 1 =================
    if match_date in source1_lookup:
        row = source1_lookup[match_date]

        if len(row) > 4:
            updates.append({"range": f"{col_letter}2", "values": [[row[4]]]})

        if len(row) > 3:
            updates.append({"range": f"{col_letter}3", "values": [[row[3]]]})

        if len(row) > 8:
            updates.append({"range": f"{col_letter}5", "values": [[row[8]]]})

    # ================= SOURCE 2 =================
    if match_date in source2_lookup:
        row = source2_lookup[match_date]

        updates.append({"range": f"{col_letter}2", "values": [["BINGO"]]})

        if len(row) > 11:
            updates.append({"range": f"{col_letter}5", "values": [[row[11]]]})

# ================= EXECUTE BATCH =================
if updates:
    suppliers.batch_update(updates)

print(f"Done. Updated {len(updates)} cells.")
