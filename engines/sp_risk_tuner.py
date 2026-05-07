import json, os, glob, numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Risk Tuner (Ultimate 4-Phase & Momentum Color)
# =====================================================================
DATA_DIR = "../data/"
OUTPUT_FILE = os.path.join(DATA_DIR, "risk_config.json")

def calculate_p80_for_window(draws, all_pairs, window):
    """ฟังก์ชันหาค่า P80 แยกตามระยะเวลา โดยใช้ลอจิกรูดหน้า-หลัง 40 ชุดเต็ม"""
    actual_window = min(window, len(draws))
    if actual_window < 5: return 0.0
    
    test_draws = draws[:actual_window]
    win_rates = []
    
    # ดึงค่าเลขผลรางวัลออกมาเป็น List ล่วงหน้าเพื่อความเร็ว (Optimization)
    results = [str(row.get('twoTop', '')).zfill(2) for row in test_draws if str(row.get('twoTop', '')).isdigit()]
    
    for pair in all_pairs:
        wins = 0
        p0, p1 = str(pair[0]), str(pair[1])
        for num in results:
            # 🔻 ลอจิก Sniper 40 ชุด: เช็คตำแหน่ง หน้า-หลัง แยกกัน (ไม่ตัดซ้ำ) 🔻
            if p0 == num[0] or p0 == num[1] or p1 == num[0] or p1 == num[1]:
                wins += 1
        win_rates.append((wins / actual_window) * 100)
    
    # คืนค่าเปอร์เซ็นไทล์ที่ 80 ของระยะนั้นๆ
    return round(float(np.percentile(win_rates, 80)), 2)

def main():
    print("\n" + "="*70)
    print("⏳ [Sengoku] วิเคราะห์เกณฑ์มาตรฐาน 4 ระยะ และตรวจสอบ Momentum ตลาด")
    print("="*70)
    
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
            
            # 🔻 1. คำนวณ P80 ครบทั้ง 4 ระยะเพื่อความแม่นยำสูงสุด 🔻
            p_15 = calculate_p80_for_window(draws, all_pairs, 15)
            p_30 = calculate_p80_for_window(draws, all_pairs, 30)
            p_60 = calculate_p80_for_window(draws, all_pairs, 60)
            p_100 = calculate_p80_for_window(draws, all_pairs, 100)
            
            # ค่าเฉลี่ยกลาง (ไม้บรรทัดหลัก)
            avg_min_wr = round((p_15 + p_30 + p_60 + p_100) / 4, 2)

            # 🔻 2. ใช้สูตร Momentum (15 vs 100) เพื่อพ่นสีสถานะ 🔻
            # เปรียบเทียบฟอร์มล่าสุด (15) กับมาตรฐานเดิม (100)
            diff = p_15 - p_100
            
            if diff >= 5:
                status_color = "🟢 [GREEN] - ตลาดขาขึ้น (Momentum +)"
            elif diff <= -5:
                status_color = "🔴 [RED] - ตลาดขาลง (Momentum -)"
            else:
                status_color = "🟡 [YELLOW] - ตลาดทรงตัว"

            multi_market_config["markets"][market_name] = {
                "p80_steps": {
                    "15d": p_15,
                    "30d": p_30,
                    "60d": p_60,
                    "100d": p_100
                },
                "dynamic_min_winrate": avg_min_wr,
                "market_health": status_color
            }
            
            print(f"🎯 {market_name.upper():<12} | เฉลี่ย: {avg_min_wr}% | Diff(15vs100): {diff:+.1f}%")
            print(f"   => สถานะ: {status_color}")

        except Exception as e:
            print(f"❌ Error ตลาด {market_name}: {e}")

    # บันทึกไฟล์ Config
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(multi_market_config, f, ensure_ascii=False, indent=4)
    
    print("="*70)
    print("✅ [Sengoku] อัปเดตไม้บรรทัด 4 ระยะและระบบสีเรียบร้อย!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
