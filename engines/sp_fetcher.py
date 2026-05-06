import gspread
from google.oauth2.service_account import Credentials
import json
import os

# ⚙️ Configuration
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
RAW_DATA_FILE = "../data/raw_excel.json"

def main():
    print("⏳ [Data Fetcher] กำลังเชื่อมต่อ Google Sheets API...")
    try:
        creds_json = os.environ.get("GCP_CREDENTIALS")
        creds = Credentials.from_service_account_info(
            json.loads(creds_json), 
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        
        ws = sheet.worksheet("NIKKEI")
        rows = ws.get_all_values()[2:] # ข้าม Header 2 แถวบน
        
        draws = []
        for r in rows:
            if not r[0] and not r[3]: # ข้ามแถวว่าง
                continue
            draws.append({
                "date": r[0],
                "open": r[1],
                "diff": r[2],
                "twoTop": r[3]
            })
            
        # ⚠️ Reverse ข้อมูลให้ "งวดล่าสุด" (ล่างสุดใน Excel) ขึ้นมาอยู่ Index 0
        draws.reverse()
            
        os.makedirs(os.path.dirname(RAW_DATA_FILE), exist_ok=True)
        with open(RAW_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(draws, f, ensure_ascii=False, indent=4)
            
        print(f"✅ [Data Fetcher] ดึงข้อมูลและ Reverse สำเร็จ! เซฟไว้ที่ {RAW_DATA_FILE}")

    except Exception as e:
        print(f"❌ [Data Fetcher] Error: {e}")

if __name__ == "__main__":
    main()
