import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
import numpy as np

# ⚙️ Configuration
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
OUTPUT_FILE = "../data/result_math.json" 

def get_data():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json), 
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def analyze_math(draws):
    """
    Logic: ใช้ Gap Analysis และ Standard Deviation
    หาเลขที่ 'อั้น' หรือเลขที่มีความเสถียรสูงสุด
    """
    scores = [0.0] * 10
    
    # 1. Gap Analysis (ระยะห่าง)
    # ดูว่าเลขแต่ละตัว (0-9) ไม่มานานแค่ไหนแล้ว
    last_seen = {i: 0 for i in range(10)}
    found = {i: False for i in range(10)}
    
    for gap, row in enumerate(draws):
        num_str = str(row['twoTop']).zfill(2)
        if len(num_str) == 2:
            d1, d2 = int(num_str[0]), int(num_str[1])
            if not found[d1]:
                last_seen[d1] = gap
                found[d1] = True
            if not found[d2]:
                last_seen[d2] = gap
                found[d2] = True
        if all(found.values()): break

    # เลขไหนหายไปนาน (Gap สูง) จะได้คะแนนสะสมเพิ่มขึ้น (กฎความน่าจะเป็นที่ต้องกลับมาค่าเฉลี่ย)
    for i in range(10):
        scores[i] += last_seen[i] * 0.5 

    # 2. Standard Deviation (ความนิ่ง)
    # คำนวณหาเลขที่มีรอบการออกสม่ำเสมอที่สุด (ไม่เหวี่ยง)
    # เหมือนเช็ก Ping ของ Server ว่านิ่งไหม
    for i in range(10):
        # วิเคราะห์ความถี่ในช่วง 50 งวดล่าสุด
        counts = 0
        for row in draws[:50]:
            if str(i) in str(row['twoTop']).zfill(2):
                counts += 1
        
        # ถ้าออกตามเกณฑ์ค่าเฉลี่ย (Standard) จะได้คะแนนโบนัส
        if 8 <= counts <= 12: # ค่าเฉลี่ยที่ควรจะเป็นคือประมาณ 10 ครั้งใน 50 งวด
            scores[i] += 10.0

    return scores

def main():
    try:
        sheet = get_data()
        ws = sheet.worksheet("NIKKEI") 
        rows = ws.get_all_values()[2:]
        
        draws = []
        for r in rows:
            draws.append({"twoTop": r[3]})
        
        # รันการคำนวณคณิตศาสตร์
        math_scores = analyze_math(draws)
        
        # จัดอันดับ
        ranked_digits = sorted(
            [(str(i), s) for i, s in enumerate(market_scores)], 
            key=lambda x: x[1], 
            reverse=True
        )
        
        result = {
            "bot_name": "Math_Probability_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": math_scores,
            "status": "success"
        }
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Math Bot Analysis Saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
