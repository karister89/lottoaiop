import json
import os
import glob
import numpy as np
from itertools import combinations

# =====================================================================
# ⚙️ แผงควบคุมหลัก (MULTI-MARKET CONFIGURATION)
# =====================================================================
DATA_DIR = "../data/"
OUTPUT_FILE = "../data/risk_config.json"

# 🌟 อัปเกรด: เตรียมส่งค่า 3 ระยะให้กุนซือ CORE (แต่ตัวมันเองใช้ 30 วันเป็นเกณฑ์วัดมาตรฐานหลัก)
BACKTEST_WINDOWS = [30, 60, 90] 
DEFAULT_WINDOW = 30 

def main():
    print(f"⏳ [Risk Tuner] กำลังสแกนหา 'เกณฑ์วินเรท' ของทุกตลาด ด้วยหลักคณิตศาสตร์ (Pure Math)...")
    try:
        # 🔍 สแกนหาไฟล์ raw_ ทั้งหมดในโฟลเดอร์ data
        raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
        if not raw_files:
            print("❌ [Risk Tuner] ไม่พบไฟล์ข้อมูลดิบ (raw_*.json) ให้วิเคราะห์!")
            return
            
        all_pairs = list(combinations(range(10), 2))
        
        # 📦 สร้างพอร์ตโฟลิโอเก็บค่าคอนฟิกของทุกตลาดรวมกัน
        multi_market_config = {
            "backtest_windows": BACKTEST_WINDOWS,
            "markets": {} # เก็บแยกรายหุ้น
        }
        
        # วนลูปเจาะลึกทีละตลาด
        for file_path in raw_files:
            market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
            print(f"\n📊 กำลังประเมินตลาด: {market_name.upper()}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)
                
            if not draws or len(draws) == 0:
                print(f"⚠️ ตลาด {market_name} ไม่มีข้อมูล ข้าม...")
                continue
                
            # ตัดข้อมูลมาแค่จำนวนงวดที่ต้องการทดสอบ (30 วัน)
            test_draws = draws[:DEFAULT_WINDOW]
            win_rates = []
            
            # 1. เทสต์เก็บข้อมูลประชากรทั้งหมด (45 คู่) ของตลาดนี้
            for pair in all_pairs:
                wins = 0
                for row in test_draws:
                    num_str = str(row.get('twoTop', '')).zfill(2)
                    if str(pair[0]) in num_str or str(pair[1]) in num_str:
                        wins += 1
                
                win_rate = (wins / len(test_draws)) * 100
                win_rates.append(win_rate)
                
            # 2. คำนวณสถิติด้วย Numpy (ของตลาดใครตลาดมัน)
            mean_wr = np.mean(win_rates)
            sd_wr = np.std(win_rates)
            p80_wr = np.percentile(win_rates, 80)
            
            recommended_min_winrate = round(p80_wr, 2)
            
            # บันทึกค่า P80, Mean, SD ประจำตลาดนี้เก็บไว้ใน Dictionary
            multi_market_config["markets"][market_name] = {
                "dynamic_min_winrate": recommended_min_winrate,
                "market_stats": {
                    "mean": round(mean_wr, 2),
                    "sd": round(sd_wr, 2)
                }
            }
            
            print(f"  👉 เส้นมาตรฐาน P80: {recommended_min_winrate}% | ค่าเฉลี่ย(Mean): {round(mean_wr, 2)}% | ความแกว่ง(SD): {round(sd_wr, 2)}")

        # 3. บันทึกไฟล์ Config รวม ส่งให้กุนซือ (CORE)
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(multi_market_config, f, ensure_ascii=False, indent=4)
            
        print(f"\n✅ [Risk Tuner] จูนสถิติสำเร็จครบ {len(raw_files)} ตลาด! (อัปเดตลง risk_config.json เรียบร้อย)")

    except Exception as e:
        print(f"❌ [Risk Tuner] Error: {e}")

if __name__ == "__main__":
    main()
