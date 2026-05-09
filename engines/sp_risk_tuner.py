import json
import os
import glob
import numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Risk Tuner (Split Front-Back Mode)
# =====================================================================
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "risk_config.json")

def calculate_p80_split(draws, all_pairs, window):
    """ฟังก์ชันหาค่า P80 แยกตามระยะเวลา โดยชำแหละแยก 'หน้า (หลักสิบ)' และ 'หลัง (หลักหน่วย)'"""
    actual_window = min(window, len(draws))
    if actual_window < 5: 
        return 0.0, 0.0
    
    test_draws = draws[:actual_window]
    wr_front = [] # เก็บวินเรทรูดหน้า
    wr_back = []  # เก็บวินเรทรูดหลัง
    
    # ดึงเลขรางวัลมาเตรียมไว้ (แยกเป็นหลักสิบและหลักหน่วย)
    results = []
    for row in test_draws:
        num = str(row.get('twoTop', '')).zfill(2)
        if num.isdigit():
            results.append((num[0], num[1])) # (สิบ, หน่วย)
    
    for pair in all_pairs:
        wins_f, wins_b = 0, 0
        p0, p1 = str(pair[0]), str(pair[1])
        
        for ten, unit in results:
            # 🔻 เช็คสมรภูมิหน้า (รูดหน้า 2 เลข) 🔻
            if p0 == ten or p1 == ten:
                wins_f += 1
            # 🔻 เช็คสมรภูมิหลัง (รูดหลัง 2 เลข) 🔻
            if p0 == unit or p1 == unit:
                wins_b += 1
                
        wr_front.append((wins_f / actual_window) * 100)
        wr_back.append((wins_b / actual_window) * 100)
    
    # คืนค่า P80 ของทั้งสองตำแหน่ง
    p80_f = round(float(np.percentile(wr_front, 80)), 2)
    p80_b = round(float(np.percentile(wr_back, 80)), 2)
    return p80_f, p80_b

def main():
    print("\n" + "="*75)
    print("⏳ [Sengoku] เริ่มสร้างไม้บรรทัดแยกส่วน: สมรภูมิหน้า (10) vs สมรภูมิหลัง (1)")
    print("="*75)
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    all_pairs = list(combinations(range(10), 2))
    multi_market_config = {"markets": {}}
    
    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)
            if not draws: continue
            
            # คำนวณ P80 แยก หน้า-หลัง ครบทั้ง 4 ระยะ
            # f = front (หน้า), b = back (หลัง)
            f15, b15 = calculate_p80_split(draws, all_pairs, 15)
            f30, b30 = calculate_p80_split(draws, all_pairs, 30)
            f60, b60 = calculate_p80_split(draws, all_pairs, 60)
            f100, b100 = calculate_p80_split(draws, all_pairs, 100)
            
            # หาเกณฑ์เฉลี่ยแยกตำแหน่ง
            avg_f = round((f15 + f30 + f60 + f100) / 4, 2)
            avg_b = round((b15 + b30 + b60 + b100) / 4, 2)

            # ตรวจสอบ Momentum แยกตำแหน่ง (15d vs 100d)
            diff_f = f15 - f100
            diff_b = b15 - b100
            
            def get_health(diff):
                if diff >= 3: return "🟢 GREEN"
                if diff <= -3: return "🔴 RED"
                return "🟡 YELLOW"

            multi_market_config["markets"][market_name] = {
                "front": {
                    "p80_steps": {"15d": f15, "30d": f30, "60d": f60, "100d": f100},
                    "min_winrate": avg_f,
                    "health": get_health(diff_f)
                },
                "back": {
                    "p80_steps": {"15d": b15, "30d": b30, "60d": b60, "100d": b100},
                    "min_winrate": avg_b,
                    "health": get_health(diff_b)
                }
            }
            
            print(f"🎯 {market_name.upper():<12}")
            print(f"   [หน้า] เกณฑ์: {avg_f}% | สถานะ: {get_health(diff_f)} (Diff: {diff_f:+.1f}%)")
            print(f"   [หลัง] เกณฑ์: {avg_b}% | สถานะ: {get_health(diff_b)} (Diff: {diff_b:+.1f}%)")

        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(multi_market_config, f, ensure_ascii=False, indent=4)
    
    print("="*75)
    print(f"✅ [Sengoku] บันทึกเกณฑ์แยกส่วนสำเร็จ! พร้อมให้ Optimizer หา Top 5 สองรอบ")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
