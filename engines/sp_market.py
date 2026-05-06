import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd

# ⚙️ Configuration
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
# เราจะเซฟไฟล์ผลลัพธ์ออกไปที่โฟลเดอร์ data
OUTPUT_FILE = "../data/result_market.json" 

def get_data():
    # ดึง Credentials จาก GitHub Secrets
    creds_json = os.environ.get("GCP_CREDENTIALS")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json), 
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def analyze_market(draws):
    """
    Logic: วิเคราะห์ความสัมพันธ์ระหว่างสภาวะตลาด (Diff) กับเลขที่ออก
    """
    scores = [0.0] * 10
    df = pd.DataFrame(draws)
    
    # แปลงข้อมูลให้เป็นตัวเลขเพื่อการคำนวณ
    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    
    # ดึงค่า Diff ล่าสุดของวันนี้มาดู (สมมติว่าเป็นแถวแรก)
    current_diff = df.iloc[0]['diff'] 
    
    # 🔍 กลยุทธ์ที่ 1: Market Direction Correlation
    # ย้อนดูสถิติ 100 งวดล่าสุดที่มีทิศทางตลาด (บวก/ลบ) เหมือนวันนี้
    if current_diff > 0:
        past_matches = df[df['diff'] > 0].head(100)
    else:
        past_matches = df[df['diff'] <= 0].head(100)

    for _, row in past_matches.iterrows():
        num_str = str(row['twoTop']).zfill(2)
        if len(num_str) == 2:
            scores[int(num_str[0])] += 1.0 # ให้คะแนนหลักสิบ
            scores[int(num_str[1])] += 1.0 # ให้คะแนนหลักหน่วย

    # 🔍 กลยุทธ์ที่ 2: Last Digit Indexing
    # ใช้เลขท้ายของค่า Open ของวันนี้มาช่วยถ่วงน้ำหนัก (มักมีความสัมพันธ์ทางจิตวิทยา)
    current_open_last_digit = str(df.iloc[0]['open'])[-1]
    if current_open_last_digit.isdigit():
        scores[int(current_open_last_digit)] += 1.5 # ให้คะแนนพิเศษ 1.5 เท่า

    return scores

def main():
    try:
        sheet = get_data()
        ws = sheet.worksheet("NIKKEI") # เริ่มต้นที่ตลาด NIKKEI
        rows = ws.get_all_values()[2:] # ข้าม Header 2 แถวแรก
        
        draws = []
        for r in rows:
            # เก็บข้อมูล: วันที่, Open, Diff, เลขที่ออก
            draws.append({
                "date": r[0], 
                "open": r[1], 
                "diff": r[2], 
                "twoTop": r[3]
            })
        
        # รันการวิเคราะห์
        market_scores = analyze_market(draws)
        
        # จัดลำดับเลข 0-9 จากคะแนนมากไปน้อย
        ranked_digits = sorted(
            [(str(i), s) for i, s in enumerate(market_scores)], 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # เตรียมข้อมูลเพื่อส่งต่อให้บอทกุนซือ (Synergy)
        result = {
            "bot_name": "Market_Whale_V1",
            "top_digits": [r[0] for r in ranked_digits], # ลำดับเลขเด่น
            "raw_scores": market_scores,
            "status": "success"
        }
        
        # ตรวจสอบและสร้างโฟลเดอร์ data ถ้ายังไม่มี (ป้องกัน Error)
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Market Bot Analysis Saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
