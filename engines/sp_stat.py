import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math

# ⚙️ Configuration
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
OUTPUT_FILE = "../data/result_stat.json" 

def get_data():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json), 
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def analyze_statistics(draws):
    """
    Logic: คำนวณความถี่แบบถ่วงน้ำหนัก (Exponential Decay)
    ยิ่งออกล่าสุด ยิ่งได้คะแนนสูง
    """
    scores = [0.0] * 10
    
    # วิเคราะห์ย้อนหลัง 100 งวด (Window Size)
    lookback = 100
    subset = draws[:lookback]
    
    for i, row in enumerate(subset):
        num_str = str(row['twoTop']).zfill(2)
        if len(num_str) == 2:
            # สูตร: 0.95 ยกกำลังลำดับความห่าง (ยิ่งห่างคะแนนยิ่งน้อย)
            weight = math.pow(0.95, i) 
            
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
            draws.append({"twoTop": r[3]}) # สายสถิติเน้นเลขที่ออกเป็นหลัก
        
        # คำนวณคะแนน
        stat_scores = analyze_statistics(draws)
        
        # จัดลำดับ
        ranked_digits = sorted(
            [(str(i), s) for i, s in enumerate(stat_scores)], 
            key=lambda x: x[1], 
            reverse=True
        )
        
        result = {
            "bot_name": "Stat_Heavy_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": stat_scores,
            "status": "success"
        }
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Stat Bot Analysis Saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
