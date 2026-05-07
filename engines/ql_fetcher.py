import gspread
from google.oauth2.service_account import Credentials
import json
import os

# =====================================================================
# ⚙️ Configuration - ตั้งค่าทัพหน้า (ดึง 8 หุ้น)
# =====================================================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
DATA_DIR = "../data/"

# ⚠️ พี่นพพลแก้ชื่อในวงเล็บนี้ ให้ตรงกับ "ชื่อแท็บ" ใน Google Sheets แบบเป๊ะๆ นะครับ 
# (พิมพ์เล็ก/ใหญ่เว้นวรรคต้องตรงกัน) เจมใส่ตัวอย่างชื่อหุ้นยอดฮิตไว้ให้ก่อนครับ
MARKETS = [
    "NIKKEI", 
    "HANGSENG", 
    "CHINA", 
    "TAIWAN", 
    "KOREA", 
    "SINGAPORE", 
    "INDIA", 
    "RUSSIA"
]

def main():
    print("⏳ [QL Fetcher] กำลังเชื่อมต่อ Google Sheets API...")
    try:
        # 1. เชื่อมต่อ API
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
        
        # สร้างโฟลเดอร์ data เตรียมไว้
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # 2. วนลูปดึงข้อมูลทีละหุ้น
        print(f"🎯 เป้าหมาย: ดึงข้อมูลทั้งหมด {len(MARKETS)} หุ้น")
        
        for market in MARKETS:
            try:
                print(f"กำลังสแกนหุ้น 📊 {market}...", end=" ")
                ws = sheet.worksheet(market)
                rows = ws.get_all_values()[2:] # ข้าม Header 2 แถวแรก
                
                draws = []
                for r in rows:
                    # ดักแถวว่าง
                    if not r[0] or not r[3]: 
                        continue
                        
                    draws.append({
                        "date": r[0],
                        "open": r[1],
                        "diff": r[2],
                        "twoTop": r[3]
                    })
                    
                # ⚠️ งวดล่าสุดอยู่บนสุด (Index 0)
                draws.reverse()
                    
                # 3. บันทึกแยกไฟล์ตามชื่อหุ้น (แปลงชื่อเป็นพิมพ์เล็กเพื่อให้ดูง่าย)
                file_name = f"raw_{market.lower().replace(' ', '_')}.json"
                save_path = os.path.join(DATA_DIR, file_name)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(draws, f, ensure_ascii=False, indent=4)
                    
                print(f"✅ สำเร็จ ({len(draws)} งวด) -> {file_name}")
                
            except gspread.exceptions.WorksheetNotFound:
                print(f"❌ ไม่พบแท็บชื่อ '{market}' (ข้ามไปตัวต่อไป)")
            except Exception as e:
                print(f"❌ Error ดึงข้อมูล {market}: {e}")

        print("🎉 [QL Fetcher] ดึงข้อมูลครบทุกหุ้นแล้ว!")

    except Exception as e:
        print(f"❌ [QL Fetcher] Critical Error ระบบล่ม: {e}")

if __name__ == "__main__":
    main()
