import json
import os
import glob
import numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Optimizer (Split Strategy 20/20)
# =====================================================================
DATA_DIR = "../data/"
RISK_CONFIG = os.path.join(DATA_DIR, "risk_config.json")
# ไฟล์รวบรวมคะแนนโหวตจากบอท 4 ตัว (Jinbe, Robin, Law, Katakuri)
VOTES_FILE = os.path.join(DATA_DIR, "bot_consensus_votes.json")
FINAL_OUTPUT = os.path.join(DATA_DIR, "optimized_pairs.json")

def calculate_bet_by_confidence(consensus_score, current_wr, p80_value):
    """สูตรคำนวณเงินเดิมพัน 0-100% ตามความมั่นใจบอทและเกณฑ์ P80"""
    # 1. ตัวกรองนิรภัย: ถ้าสถิติ (Win Rate) ต่ำกว่าไม้บรรทัด (P80) ให้หยุดทันที
    if current_wr < p80_value:
        return 0, "🔴 RED"
    
    # 2. คำนวณน้ำหนักเงินตามจำนวนบอทที่โหวตตรงกัน (เพิ่ม-ลดทีละ 10)
    if consensus_score >= 4:
        bet_size = 100
        status = "🟢 GREEN"
    elif consensus_score == 3:
        bet_size = 90
        status = "🟡 YELLOW"
    elif consensus_score == 2:
        bet_size = 60 # เริ่มต้นที่ 60 ตามลอจิกความเสี่ยง
        status = "🟡 YELLOW"
    else:
        bet_size = 0
        status = "🔴 RED"
        
    return bet_size, status

def backtest_position(draws, pair, position='front'):
    """จำลองการแทงย้อนหลัง 30 งวด เพื่อหาวินเรทและกำไรแยกตำแหน่ง"""
    wins = 0
    p0, p1 = str(pair[0]), str(pair[1])
    test_draws = draws[:30] # ตรวจสอบความสด 30 งวดล่าสุด
    
    for row in test_draws:
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
        
        target = num[0] if position == 'front' else num[1]
        if p0 == target or p1 == target:
            wins += 1
            
    win_rate = (wins / len(test_draws)) * 100
    profit = (wins * 90) - (len(test_draws) * 20) # ทุน 20 ต่อรอบ
    return win_rate, profit

def hunt_best_pair(draws, votes, p80_min, pos='front'):
    """ลอจิกการหา Top 5 และคัดเลือกคู่เลขที่ดีที่สุดประจำตำแหน่ง"""
    all_pairs = list(combinations(range(10), 2))
    candidates = []

    for pair in all_pairs:
        # ดึงคะแนนความมั่นใจ (จำนวนบอทที่โหวตเลขตัวนี้)
        v1 = votes.get(str(pair[0]), 0)
        v2 = votes.get(str(pair[1]), 0)
        # คะแนนรวม (Consensus Score) เต็ม 4
        c_score = max(v1, v2) # ใช้ค่าสูงสุดของหนึ่งในคู่เลข หรือปรับตามลอจิกพี่

        wr, profit = backtest_position(draws, pair, pos)
        
        # คัดเฉพาะตัวที่ผ่านเกณฑ์ P80
        if wr >= p80_min:
            candidates.append({
                "pair": pair,
                "score": c_score,
                "win_rate": wr,
                "profit": profit
            })

    # เรียงลำดับคัด Top 5: เน้นคะแนนโหวตนำ (ความมั่นใจ) ตามด้วยกำไรสะสม
    candidates.sort(key=lambda x: (x['score'], x['profit']), reverse=True)
    
    if not candidates:
        return None

    best = candidates[0]
    # คำนวณ Bet Size และสถานะสี
    bet, status = calculate_bet_by_confidence(best['score'], best['win_rate'], p80_min)
    
    return {
        "pair": best['pair'],
        "win_rate": best['win_rate'],
        "profit": best['profit'],
        "bet_size": bet,
        "status": status,
        "score": best['score']
    }

def main():
    print("\n" + "🚀 [Law] อัปเกรดระบบ: แยกสมรภูมิ + เดินเงินตามความมั่นใจ 0-100%")
    
    with open(RISK_CONFIG, 'r', encoding='utf-8') as f:
        risk_data = json.load(f)

    # โหลดคะแนนโหวตสะสมจากกุนซือทั้ง 4 (Jinbe, Robin, Law, Katakuri)
    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            votes_data = json.load(f)
    except:
        votes_data = {} # กรณีหาไฟล์ไม่เจอ

    results = {"markets": {}}

    for market, config in risk_data['markets'].items():
        raw_file = os.path.join(DATA_DIR, f"raw_{market}.json")
        if not os.path.exists(raw_file): continue

        with open(raw_file, 'r', encoding='utf-8') as f:
            draws = json.load(f)

        print(f"🔎 วิเคราะห์ตลาด: {market.upper()}")

        # 🎯 รอบที่ 1: หาตัวเด่นสำหรับ 'รูดหน้า' (หลักสิบ)
        best_f = hunt_best_pair(draws, votes_data.get(market, {}), config['front']['min_winrate'], 'front')
        
        # 🎯 รอบที่ 2: หาตัวเด่นสำหรับ 'รูดหลัง' (หลักหน่วย)
        best_b = hunt_best_pair(draws, votes_data.get(market, {}), config['back']['min_winrate'], 'back')

        results["markets"][market] = {
            "front": best_f,
            "back": best_b,
            "last_update": "2026-05-08"
        }
        
        # แสดงผล Log ให้พี่ดูหน้าจอ
        f_info = f"{best_f['pair']} ({best_f['bet_size']}%)" if best_f else "🔴 SKIP"
        b_info = f"{best_b['pair']} ({best_b['bet_size']}%)" if best_b else "🔴 SKIP"
        print(f"   [หน้า]: {f_info} | [หลัง]: {b_info}")

    with open(FINAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\n✅ วิเคราะห์เสร็จสิ้น! ข้อมูลพร้อมส่งเข้าศูนย์บัญชาการแล้วครับพี่นพพล\n")

if __name__ == "__main__":
    main()
