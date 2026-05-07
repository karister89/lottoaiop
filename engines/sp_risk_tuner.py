import json, os, glob, numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Risk Tuner (Multi-Dimensional P80)
# =====================================================================
DATA_DIR = "../data/"
OUTPUT_FILE = "../data/risk_config.json"

def calculate_p80_for_window(draws, all_pairs, window):
    """ฟังก์ชันหาค่า P80 แยกตามระยะเวลาที่กำหนด"""
    actual_window = min(window, len(draws))
    if actual_window < 5: return 0
    
    test_draws = draws[:actual_window]
    win_rates = []
    
    for pair in all_pairs:
        # เช็คว่าเลขคู่ไหนใน 45 คู่ มีวินเรทเท่าไหร่ในระยะนี้
        wins = sum(1 for row in test_draws if any(str(p) in str(row.get('twoTop', '')).zfill(2) for p in pair))
        win_rates.append((wins / actual_window) * 100)
    
    # คืนค่าเปอร์เซ็นไทล์ที่ 80 ของระยะนั้นๆ
    return round(np.percentile(win_rates, 80), 2)

def main():
    print("⏳ [Risk Tuner] กำลังสร้างเกณฑ์มาตรฐานหลายมิติ (15/30/60/100 วัน)...")
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    all_pairs = list(combinations(range(10), 2))
    
    multi_market_config = {"markets": {}}
    
    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            draws = json.load(f)
        if not draws: continue
        
        # 🔻 คำนวณเกณฑ์แยกตามระยะ 🔻
        p80_15 = calculate_p80_for_window(draws, all_pairs, 15)
        p80_30 = calculate_p80_for_window(draws, all_pairs, 30)
        p80_60 = calculate_p80_for_window(draws, all_pairs, 60)
        p80_100 = calculate_p80_for_window(draws, all_pairs, 100)
        
        # ใช้ค่าเฉลี่ยของ P80 ทุกระยะเป็น "เกณฑ์กลาง" ที่ยุติธรรมที่สุด (Dynamic Min Winrate)
        combined_min_winrate = round((p80_15 + p80_30 + p80_60 + p80_100) / 4, 2)
        
        multi_market_config["markets"][market_name] = {
            "p80_steps": {
                "15d": p80_15,
                "30d": p80_30,
                "60d": p80_60,
                "100d": p80_100
            },
            "dynamic_min_winrate": combined_min_winrate # ส่งตัวนี้ไปให้ Money Commander ใช้
        }
        
        print(f"   ⚖️ {market_name.upper()} | เกณฑ์ P80: [15d: {p80_15}% | 100d: {p80_100}%] -> เฉลี่ยกลาง: {combined_min_winrate}%")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(multi_market_config, f, ensure_ascii=False, indent=4)
    
    print(f"\n✅ [Risk Tuner] อัปเกรดเกณฑ์มาตรฐานหลายมิติสำเร็จ!")

if __name__ == "__main__":
    main()
