import json
import os
import glob
import pandas as pd

# =====================================================================
# ⚙️ Configuration - SP Market (V3 - Split Position)
# =====================================================================
DATA_DIR = "../data/"

def analyze_market_split(draws):
    """
    🔻 สมการออริจินัล: แยกน้ำหนักคะแนน หน้า (หลักสิบ) และ หลัง (หลักหน่วย) 🔻
    """
    scores_f = [0.0] * 10 # คะแนนหลักสิบ
    scores_b = [0.0] * 10 # คะแนนหลักหน่วย
    df = pd.DataFrame(draws)
    
    if df.empty: 
        return scores_f, scores_b

    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    current_diff = df.iloc[0]['diff'] 
    
    # แยกกลุ่มข้อมูลตาม Diff (บวก/ลบ) เหมือนสูตรเดิมของพี่
    if current_diff > 0:
        past_matches = df[df['diff'] > 0].head(100)
    else:
        past_matches = df[df['diff'] <= 0].head(100)

    for _, row in past_matches.iterrows():
        num_str = str(row.get('twoTop', '')).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
            # 🎯 จุดเปลี่ยน: บันทึกคะแนนแยกตามตำแหน่งที่เลขนั้นเคยปรากฏ
            scores_f[int(num_str[0])] += 1.0 # เก็บสถิติเลขที่ชอบมาหลักสิบ
            scores_b[int(num_str[1])] += 1.0 # เก็บสถิติเลขที่ชอบมาหลักหน่วย

    # วิเคราะห์เลขท้ายราคาเปิด (Open) ตามสูตรของพี่
    current_open_last_digit = str(df.iloc[0]['open'])[-1]
    if current_open_last_digit.isdigit():
        digit = int(current_open_last_digit)
        # ให้คะแนนพิเศษทั้งสองตำแหน่ง (เพราะเลขเปิดมีอิทธิพลสูง)
        scores_f[digit] += 1.5 
        scores_b[digit] += 1.5 

    return scores_f, scores_b

def main():
    print("⏳ [SP Market] วิเคราะห์แนวโน้มตลาดแยกตำแหน่ง (Front-Back)...")
    
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
            
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)

            if not draws: continue

            print(f"🔍 กำลังคำนวณตลาด: {market_name.upper()}")
            
            # 🎯 เรียกใช้ฟังก์ชันแยกคะแนน หน้า-หลัง
            sc_f, sc_b = analyze_market_split(draws)
            
            # จัดอันดับท็อป 5 ของแต่ละตำแหน่ง
            top_f = sorted(range(10), key=lambda i: sc_f[i], reverse=True)
            top_b = sorted(range(10), key=lambda i: sc_b[i], reverse=True)
            
            result = {
                "bot_name": "Market_Jinbe_V3",
                "market": market_name,
                "front_scores": sc_f, # คะแนนหลักสิบส่งให้แม่ทัพ
                "back_scores": sc_b,  # คะแนนหลักหน่วยส่งให้แม่ทัพ
                "top_front": top_f[:5],
                "top_back": top_b[:5],
                "status": "success"
            }
            
            out_file = os.path.join(DATA_DIR, f"result_market_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
                
            print(f"  ✅ บันทึกสำเร็จ -> result_market_{market_name}.json")
            
        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

    print("🎉 [SP Market] วิเคราะห์แยกตำแหน่งเสร็จสิ้น!")

if __name__ == "__main__":
    main()
