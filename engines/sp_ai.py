import json
import os
import glob
import pandas as pd

DATA_DIR = "data"

def analyze_pattern_split(draws):
    """
    🔻 AI Pattern Matching: แยกน้ำหนักคะแนน หน้า-หลัง 🔻
    """
    scores_f = [0.0] * 10 # คะแนนสำหรับหลักสิบ
    scores_b = [0.0] * 10 # คะแนนสำหรับหลักหน่วย
    
    df = pd.DataFrame(draws)
    if df.empty or len(df) < 2:
        return scores_f, scores_b
        
    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    current_diff = df.iloc[0]['diff']
    
    df['distance'] = abs(df['diff'] - current_diff)
    similar_past = df.iloc[1:].sort_values(by='distance').head(30)
    
    for index, row in similar_past.iterrows():
        two_top = row.get('twoTop', '')
        if pd.isna(two_top) or not two_top: continue
            
        num_str = str(two_top).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
            # คำนวณน้ำหนักตามความคล้าย
            weight = 1.0 / (row['distance'] + 0.1) 
            
            # 🎯 แยกเก็บคะแนนตามตำแหน่งจริงที่เคยออก
            scores_f[int(num_str[0])] += weight # ให้คะแนนเลขที่เคยออกหลักสิบ
            scores_b[int(num_str[1])] += weight # ให้คะแนนเลขที่เคยออกหลักหน่วย

    return scores_f, scores_b

def main():
    print("⏳ [SP AI] วิเคราะห์แพทเทิร์นแยกตำแหน่ง (Front-Back)...")
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)
            if not draws: continue

            # 🤖 AI วิเคราะห์แยกคะแนนหน้า-หลัง
            sc_f, sc_b = analyze_pattern_split(draws)
            
            # จัดอันดับท็อปของแต่ละฝั่ง
            top_f = sorted(range(10), key=lambda i: sc_f[i], reverse=True)
            top_b = sorted(range(10), key=lambda i: sc_b[i], reverse=True)
            
            result = {
                "bot_name": "AI_Katakuri_V3",
                "market": market_name,
                "front_scores": sc_f, # ส่งคะแนนหลักสิบไปให้กุนซือใหญ่
                "back_scores": sc_b,  # ส่งคะแนนหลักหน่วยไปให้กุนซือใหญ่
                "top_front": top_f[:5],
                "top_back": top_b[:5],
                "status": "success"
            }
            
            out_file = os.path.join(DATA_DIR, f"result_ai_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)
                
            print(f"  ✅ {market_name.upper()} -> แยกวิเคราะห์ หน้า/หลัง สำเร็จ")
            
        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

if __name__ == "__main__":
    main()
