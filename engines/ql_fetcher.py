import gspread
from google.oauth2.service_account import Credentials
import json
import os

# =====================================================================
# ⚙️ Configuration - ทัพหน้า (Auto-Detect ดึงทุกหุ้นอัตโนมัติ)
# =====================================================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
DATA_DIR = "../data/"

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
        
        # 🌟 จุดสำคัญ: ให้บอทกวาดอ่าน "ชื่อแท็บทั้งหมด" ในไฟล์ด้วยตัวเอง
        all_worksheets = sheet.worksheets()
        print(f"🎯 ตรวจพบข้อมูลทั้งหมด {len(all_worksheets)} แท็บ กำลังเริ่มสแกน...")
        
        for ws in all_worksheets:
            market_name = ws.title # ดึงชื่อแท็บของพี่มาใช้ตรงๆ เลย (เช่น "นิคเคอิ")
            try:
                print(f"กำลังดึงข้อมูลหุ้น 📊 {market_name}...", end=" ")
                rows = ws.get_all_values()[2:] # ข้าม Header 2 แถวแรก
                
                draws = []
                for r in rows:
                    # ดัก Error กรณีแถวว่าง หรือคอลัมน์ไม่ครบ
                    if len(r) < 4 or not r[0] or not r[3]: 
                        continue
                        
                    draws.append({
                        "date": r[0],
                        "open": r[1],
                        "diff": r[2],
                        "twoTop": r[3]
                    })
                    
                # ถ้าแท็บไหนว่างเปล่าให้ข้ามไป
                if not draws:
                    print("⚠️ ไม่มีข้อมูล (ข้าม)")
                    continue

                # กลับหัวข้อมูลให้งวดล่าสุดอยู่บนสุด (Index 0)
                draws.reverse() 
                    
                # บันทึกเป็นไฟล์ชื่อเดียวกับแท็บเลย เช่น raw_นิคเคอิ.json
                file_name = f"raw_{market_name}.json"
                save_path = os.path.join(DATA_DIR, file_name)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(draws, f, ensure_ascii=False, indent=4)
                    
                print(f"✅ สำเร็จ ({len(draws)} งวด) -> {file_name}")
                
            except Exception as e:
                print(f"❌ Error ตอนดึงข้อมูลแท็บ {market_name}: {e}")

        print("🎉 [QL Fetcher] ดึงข้อมูลเสร็จสมบูรณ์ เตรียมส่งต่อให้บอทวิเคราะห์!")

    except Exception as e:
        print(f"❌ [QL Fetcher] Critical Error ระบบล่ม: {e}")

if __name__ == "__main__":
    main()
