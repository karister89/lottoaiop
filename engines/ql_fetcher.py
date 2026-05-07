import gspread
from google.oauth2.service_account import Credentials
import json
import os

# =====================================================================
# ⚙️ Configuration - ตั้งชื่อให้สื่อถึงหน่วย QL (Query & Load)
# =====================================================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
# เปลี่ยนชื่อตัวแปรให้เป็นมาตรฐานกลางที่ตัวอื่นจะเรียกใช้
RAW_DATA_FILE = "../data/raw_excel.json" 

def main():
    print("⏳ [QL Fetcher] กำลังเชื่อมต่อ Google Sheets API...")
    try:
        # ดึง Credential จาก Environment Variable ของ GitHub
        creds_json = os.environ.get("GCP_CREDENTIALS")
        if not creds_json:
            print("❌ Error: ไม่พบ GCP_CREDENTIALS ใน Environment")
            return

        creds = Credentials.from_service_account_info(
            json.loads(creds_json), 
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        
        # เลือก Worksheet เป้าหมาย
        ws = sheet.worksheet("NIKKEI")
        rows = ws.get_all_values()[2:] # ข้าม Header 2 แถวแรก
        
        draws = []
        for r in rows:
            # ดักแถวว่าง เพื่อป้องกัน Error เวลาบอทตัวอื่นเอาไปคำนวณ
            if not r[0] or not r[3]: 
                continue
                
            draws.append({
                "date": r[0],
                "open": r[1],
                "diff": r[2],
                "twoTop": r[3]
            })
            
        # ⚠️ หัวใจสำคัญ: Reverse ข้อมูลให้ "งวดล่าสุด" อยู่บนสุด (Index 0)
        # เพื่อให้บอทสาย SP และ CORE ไม่ต้องมโนลำดับงวดเอง
        draws.reverse()
            
        # บันทึกข้อมูลดิบลงไฟล์ JSON
        os.makedirs(os.path.dirname(RAW_DATA_FILE), exist_ok=True)
        with open(RAW_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(draws, f, ensure_ascii=False, indent=4)
            
        print(f"✅ [QL Fetcher] ดึงข้อมูลและจัดลำดับสำเร็จ! จำนวน {len(draws)} งวด")
        print(f"📁 บันทึกข้อมูลดิบไว้ที่: {RAW_DATA_FILE}")

    except Exception as e:
        print(f"❌ [QL Fetcher] Critical Error: {e}")

if __name__ == "__main__":
    main()
