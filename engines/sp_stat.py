import json
import os
import glob
import math

# =====================================================================
# ⚙️ Configuration - SP Stat (V3 - Split Position)
# =====================================================================
DATA_DIR = "../data/"

def analyze_statistics_split(draws):
    """
    🔻 สมการออริจินัล: Exponential Decay (แยกน้ำหนัก หน้า-หลัง) 🔻
    ยิ่งงวดล่าสุด ยิ่งได้คะแนนสูง โดยแยกตามตำแหน่งจริง
    """
    scores_f = [0.0] * 10 # คะแนนความสดหลักสิบ
    scores_b = [0.0] * 10 # คะแนนความสดหลักหน่วย
    
    lookback = 100
    subset = draws[:lookback]
    
    for i, row in enumerate(subset):
        two_top = row.get('twoTop', '')
        if not two_top: continue
            
        num_str = str(two_top).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
            # คำนวณน้ำหนัก (ฐาน 0.95: ยิ่งเก่ายิ่งค่าลดลงเร็ว)
            weight = math.pow(0.95, i) 
            
            # 🎯 บันทึกคะแนนแยกตำแหน่ง
            scores_f[int(num_str[0])] += weight # เลขนี้สดในหลักสิบ
            scores_b[int(num_str[1])] += weight # เลขนี้สดในหลักหน่วย
            
    return scores_f, scores_b

def main():
    print("⏳ [SP Stat] วิเคราะห์สถิติความสดแยกตำแหน่ง (Front-Back)...")
    
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
            
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)

            if not draws: continue

            print(f"📊 วิเคราะห์ความสดหุ้น: {market_name.upper()}")
            
            # 🎯 คำนวณแยกคะแนน หน้า-หลัง
            sc_f, sc_b = analyze_statistics_split(draws)
            
            # จัดอันดับท็อป 5 ของแต่ละตำแหน่ง
            top_f = sorted(range(10), key=lambda i: sc_f[i], reverse=True)
            top_b = sorted(range(10), key=lambda i: sc_b[i], reverse=True)
            
            result = {
                "bot_name": "Stat_Robin_V3",
                "market": market_name,
                "front_scores": sc_f,
                "back_scores": sc_b,
                "top_front": top_f[:5],
                "top_back": top_b[:5],
                "status": "success"
            }
            
            out_file = os.path.join(DATA_DIR, f"result_stat_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)
                
            print(f"  ✅ บันทึกสำเร็จ -> result_stat_{market_name}.json")
            
        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

    print("🎉 [SP Stat] วิเคราะห์แยกตำแหน่งเสร็จสิ้นครบทุกตลาด!")

if __name__ == "__main__":
    main()
