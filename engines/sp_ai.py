import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd

# ⚙️ Configuration
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
OUTPUT_FILE = "../data/result_ai.json" 

def get_data():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json), 
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def analyze_pattern(draws):
    """
    Logic: K-Nearest Neighbors (KNN) แบบพื้นฐาน
    ค้นหางวดในอดีตที่มีสภาวะตลาด (Diff) ใกล้เคียงกับวันนี้ที่สุด
    """
    scores = [0.0] * 10
    df = pd.DataFrame(draws)
    
    # แปลงข้อมูลเป็นตัวเลข
    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    
    # ดึงค่า Diff ล่าสุด (สภาวะตลาดของวันนี้)
    current_diff = df.iloc[0]['diff']
    
    # สร้างคอลัมน์ 'distance' เพื่อหาความต่างระหว่างสภาวะตลาดวันนี้ กับอดีตแต่ละงวด
    # ยิ่งค่า distance ใกล้ 0 แปลว่าสภาวะตลาดวันนั้น "เหมือน" วันนี้มากที่สุด
    df['distance'] = abs(df['diff'] - current_diff)
    
    # ตัดข้อมูลวันนี้ออก (ไม่เอามาเทียบกับตัวเอง) แล้วเรียงลำดับหาอดีตที่คล้ายที่สุด 30 อันดับแรก
    similar_past = df.iloc[1:].sort_values(by='distance').head(30)
    
    # ให้คะแนนเลขที่เคยออกในวันที่สภาวะตลาดคล้ายวันนี้
    for index, row in similar_past.iterrows():
        num_str = str(row['twoTop']).zfill(2)
        
        # ถ่วงน้ำหนัก: ยิ่งเหตุการณ์นั้นคล้ายวันนี้มาก (distance ต่ำ) ยิ่งได้คะแนนโหวตสูง
        # ป้องกัน division by zero โดยบวกค่าเล็กน้อยเข้าไป
        weight = 1.0 / (row['distance'] + 0.1) 
        
        if len(num_str) == 2:
            scores[int(num_str[0])] += weight
            scores[int(num_str[1])] += weight

    return scores

def main():
    try:
        sheet = get_data()
        ws = sheet.worksheet("NIKKEI") 
        rows = ws.get_all_values()[2:]
        
        draws = []
        for r in rows:
            draws.append({
                "date": r[0],
                "diff": r[2],
                "twoTop": r[3]
            })
        
        # รันการค้นหาแพทเทิร์น
        ai_scores = analyze_pattern(draws)
        
        # จัดอันดับ 0-9
        ranked_digits = sorted(
            [(str(i), s) for i, s in enumerate(ai_scores)], 
            key=lambda x: x[1], 
            reverse=True
        )
        
        result = {
            "bot_name": "AI_Pattern_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": ai_scores,
            "status": "success"
        }
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"✅ AI Bot Analysis Saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
