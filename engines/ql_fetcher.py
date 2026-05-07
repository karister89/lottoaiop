import gspread
from google.oauth2.service_account import Credentials
import json
import os

# =====================================================================
# ⚙️ Configuration - ตั้งค่าทัพหน้า (Multi-Market Data Fetcher)
# =====================================================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
DATA_DIR = "../data/"

# 🗺️ แมพปิ้งชื่อแท็บภาษาไทย -> เป็นชื่อไฟล์ภาษาอังกฤษ (ป้องกัน Error ภาษา)
# ถ้าพี่นพพลต้องการใช้แค่ 8 หุ้น สามารถลบบรรทัดที่ 9-12 ทิ้งได้เลยครับ
MARKETS = {
    "นิคเคอิ": "nikkei",
    "จีน": "china",
    "ฮั่งเส็ง": "hangseng",
    "ไต้หวัน": "taiwan",
    "เกาหลี": "korea",
    "สิงคโปร์": "singapore",
    "อินเดีย": "india",
    "รัสเซีย": "russia",
    "เยอรมัน": "germany",
    "อังกฤษ": "uk",
    "ดาวโจนส์": "dowjones",
    "อียิปต์": "egypt"
}

def main():
    print("⏳ [QL Fetcher] กำลังเชื่อมต่อ Google Sheets API...")
    try:
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
        
        os.makedirs(DATA_DIR, exist_ok=True)
        
        print(f"🎯 เป้าหมาย: ดึงข้อมูลทั้งหมด {len(MARKETS)} หุ้น")
        
        # วนลูปดึงข้อมูลตามชื่อแท็บภาษาไทย
        for th_name, en_name in MARKETS.items():
            try:
                print(f"กำลังสแกนหุ้น 📊 {th_name}...", end=" ")
                ws = sheet.worksheet(th_name)
                rows = ws.get_all_values()[2:] # ข้าม Header 2 แถวแรก
                
                draws = []
                for r in rows:
                    if not r[0] or not r[3]: continue
                        
                    draws.append({
                        "date": r[0],
                        "open": r[1],
                        "diff": r[2],
                        "twoTop": r[3]
                    })
                    
                draws.reverse() # งวดล่าสุดอยู่บนสุด
                    
                # บันทึกเป็นชื่อไฟล์ภาษาอังกฤษ
                file_name = f"raw_{en_name}.json"
                save_path = os.path.join(DATA_DIR, file_name)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(draws, f, ensure_ascii=False, indent=4)
                    
                print(f"✅ สำเร็จ ({len(draws)} งวด) -> {file_name}")
                
            except gspread.exceptions.WorksheetNotFound:
                print(f"❌ ไม่พบแท็บชื่อ '{th_name}' (ข้ามไปตัวต่อไป)")
            except Exception as e:
                print(f"❌ Error ดึงข้อมูล {th_name}: {e}")

        print("🎉 [QL Fetcher] ดึงข้อมูลครบทุกหุ้นแล้วเตรียมส่งต่อให้บอทวิเคราะห์!")

    except Exception as e:
        print(f"❌ [QL Fetcher] Critical Error ระบบล่ม: {e}")

if __name__ == "__main__":
    main()
