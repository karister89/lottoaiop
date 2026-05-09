import json
import os
import glob
import numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Risk Tuner (V3 Stability & Momentum Edition)
# =====================================================================
DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "risk_config.json")

def calculate_p80_split(draws, all_pairs, window):
    """ฟังก์ชันหาค่า P80 แยกตามระยะเวลา โดยชำแหละแยก 'หน้า (หลักสิบ)' และ 'หลัง (หลักหน่วย)'"""
    actual_window = min(window, len(draws))
    if actual_window < 5: 
        return 0.0, 0.0
    
    test_draws = draws[:actual_window]
    wr_front = [] 
    wr_back = []  
    
    results = []
    for row in test_draws:
        num = str(row.get('twoTop', '')).zfill(2)
        if num.isdigit():
            results.append((num[0], num[1]))
    
    for pair in all_pairs:
        wins_f, wins_b = 0, 0
        p0, p1 = str(pair[0]), str(pair[1])
        
        for ten, unit in results:
            if p0 == ten or p1 == ten: wins_f += 1
            if p0 == unit or p1 == unit: wins_b += 1
                
        wr_front.append((wins_f / actual_window) * 100)
        wr_back.append((wins_b / actual_window) * 100)
    
    p80_f = round(float(np.percentile(wr_front, 80)), 2)
    p80_b = round(float(np.percentile(wr_back, 80)), 2)
    return p80_f, p80_b

def main():
    print("\n" + "="*75)
    print("⏳ [Sengoku] อัปเดต: ระบบสร้างเกณฑ์วัดผลแบบเน้นความเสถียร (Stability Mode)")
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
            
            # คำนวณ P80 แยก หน้า-หลัง ทั้ง 4 ระยะ
            f15, b15 = calculate_p80_split(draws, all_pairs, 15)
            f30, b30 = calculate_p80_split(draws, all_pairs, 30)
            f60, b60 = calculate_p80_split(draws, all_pairs, 60)
            f100, b100 = calculate_p80_split(draws, all_pairs, 100)
            
            # 🌟 ปรับเกณฑ์เฉลี่ยใหม่: ให้ความสำคัญกับความสม่ำเสมอระยะกลาง-ยาว
            # (15d*0.1) + (30d*0.3) + (60d*0.3) + (100d*0.3)
            avg_f = round((f15*0.1 + f30*0.3 + f60*0.3 + f100*0.3), 2)
            avg_b = round((b15*0.1 + b30*0.3 + b60*0.3 + b100*0.3), 2)

            def get_health(diff):
                if diff >= 5: return "🟢 GREEN"
                if diff <= -5: return "🔴 RED"
                return "🟡 YELLOW"

            multi_market_config["markets"][market_name] = {
                "front": {
                    "p80_steps": {"15d": f15, "30d": f30, "60d": f60, "100d": f100},
                    "min_winrate": avg_f,
                    "health": get_health(f15 - f100)
                },
                "back": {
                    "p80_steps": {"15d": b15, "30d": b30, "60d": b60, "100d": b100},
                    "min_winrate": avg_b,
                    "health": get_health(b15 - b100)
                }
            }
            
            print(f"🎯 {market_name.upper():<12}")
            print(f"   [หน้า] เกณฑ์นิ่ง: {avg_f}% | สุขภาพ: {multi_market_config['markets'][market_name]['front']['health']}")
            print(f"   [หลัง] เกณฑ์นิ่ง: {avg_b}% | สุขภาพ: {multi_market_config['markets'][market_name]['back']['health']}")

        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(multi_market_config, f, ensure_ascii=False, indent=4)
    
    print("="*75)
    print(f"✅ [Sengoku] บันทึกเกณฑ์ความเสถียรสำเร็จ! พร้อมส่งต่อให้ Optimizer")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
