import json
import os
import numpy as np
from itertools import combinations

# =====================================================================
# ⚙️ แผงควบคุมหลัก (CONFIGURATION)
# =====================================================================
RAW_DATA_FILE = "../data/raw_excel.json"
OUTPUT_FILE = "../data/risk_config.json"
BACKTEST_WINDOW = 30 # จำนวนงวดที่ใช้สแกนหามาตรฐานตลาด (ปรับเป็น 50 ได้ถ้าต้องการดูเทรนด์ยาวขึ้น)

def get_local_data():
    """อ่านข้อมูลดิบที่ดึงมาจากทัพหน้า"""
    if os.path.exists(RAW_DATA_FILE):
        with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def main():
    print(f"⏳ [Risk Tuner] กำลังสแกนหา 'เกณฑ์วินเรท' ย้อนหลัง {BACKTEST_WINDOW} งวด ด้วยหลักคณิตศาสตร์ (Pure Math)...")
    try:
        draws = get_local_data()
        if not draws:
            print(f"❌ Error: ไม่พบไฟล์ข้อมูล {RAW_DATA_FILE} (กรุณารัน sp_fetcher.py ก่อน)")
            return
            
        # ตัดข้อมูลมาแค่จำนวนงวดที่ต้องการทดสอบ (ดึงหน้าจอ Dashboard ปัจจุบัน)
        test_draws = draws[:BACKTEST_WINDOW]
        
        # สร้างคู่เลขที่เป็นไปได้ทั้งหมด 45 คู่ (00-99 รูดหน้า-หลัง)
        all_pairs = list(combinations(range(10), 2))
        win_rates = []
        
        # 1. เทสต์เก็บข้อมูลประชากรทั้งหมด (45 คู่) 
        for pair in all_pairs:
            wins = 0
            for row in test_draws:
                num_str = str(row.get('twoTop', '')).zfill(2)
                # ถ้ารูดหน้าหรือหลังเข้า นับเป็น 1 Win
                if str(pair[0]) in num_str or str(pair[1]) in num_str:
                    wins += 1
            
            # คำนวณ Win Rate ของคู่นี้แล้วเก็บใส่ list
            win_rate = (wins / len(test_draws)) * 100
            win_rates.append(win_rate)
            
        # 2. คำนวณสถิติด้วย Numpy (คณิตศาสตร์ล้วน ไม่มีการมโนตัวเลขแทรกแซง)
        mean_wr = np.mean(win_rates) # ค่าเฉลี่ยของตลาดโดยรวม
        sd_wr = np.std(win_rates)    # ค่าความแกว่ง (SD) ของตลาด
        
        # หาค่า Percentile ที่ 80 (เส้นมาตรฐานของกลุ่ม Top 20% ของตลาด ณ เวลานี้)
        p80_wr = np.percentile(win_rates, 80) 
        
        recommended_min_winrate = round(p80_wr, 2)
        
        # 3. สร้าง Config File ส่งให้กุนซือ (engine_synergy.py)
        config = {
            "backtest_window": BACKTEST_WINDOW,
            "dynamic_min_winrate": recommended_min_winrate,
            "market_stats": {
                "mean": round(mean_wr, 2),
                "sd": round(sd_wr, 2)
            },
            "status": "success"
        }
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
            
        print(f"✅ [Risk Tuner] จูนสถิติสำเร็จ! (วิเคราะห์ประชากรครบ 45 รูปแบบ)")
        print(f"📊 ค่าเฉลี่ยตลาด (Mean): {round(mean_wr, 2)}% | ความแกว่ง (SD): {round(sd_wr, 2)}")
        print(f"🎯 เส้นมาตรฐาน (P80 - Top 20%): {recommended_min_winrate}% (ส่งค่านี้ให้กุนซือแล้ว!)")

    except Exception as e:
        print(f"❌ [Risk Tuner] Error: {e}")

if __name__ == "__main__":
    main()
