import json
import os
import glob
import numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Optimizer (V3 Weighted Split Strategy 20/20)
# =====================================================================
DATA_DIR = "/data/"
RISK_CONFIG = os.path.join(DATA_DIR, "risk_config.json")
# ไฟล์รวบรวมคะแนนโหวต (แบบถ่วงน้ำหนักความเก่งแล้ว)
VOTES_FILE = os.path.join(DATA_DIR, "bot_consensus_votes.json")
FINAL_OUTPUT = os.path.join(DATA_DIR, "optimized_pairs.json")

def calculate_weighted_bet(pair_weight_score, current_wr, p80_value):
    """สูตรคำนวณเงินเดิมพัน 0-100% ตามน้ำหนักความเก่งบอท (Weight)"""
    # 1. ตัวกรองนิรภัย: สถิติปัจจุบันต้องผ่านเกณฑ์ P80 ก่อน
    if current_wr < p80_value:
        return 0, "🔴 RED"
    
    # 2. พิจารณาจาก "คะแนนความมั่นใจรวม" ของคู่เลข
    # เต็มที่คือประมาณ 2.0 (ถ้าบอททุกตัวเทใจให้ทั้งสองเลข)
    if pair_weight_score >= 1.20:
        bet_size = 100
        status = "🟢 GREEN"
    elif pair_weight_score >= 0.80:
        bet_size = 90
        status = "🟡 YELLOW"
    elif pair_weight_score >= 0.40:
        bet_size = 60 
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
    profit = (wins * 90) - (len(test_draws) * 20) # ทุน 20 ต่อรอบ (แยกรูด)
    return win_rate, profit

def hunt_best_pair(draws, market_votes, p80_min, pos='front'):
    """ลอจิกคัดเลือกคู่เลขที่ 'บอทตัวท็อป' มั่นใจที่สุด ประจำตำแหน่ง"""
    all_pairs = list(combinations(range(10), 2))
    candidates = []
    
    # เจาะจงดึงคะแนนโหวตเฉพาะตำแหน่ง (front หรือ back)
    pos_votes = market_votes.get(pos, {})

    for pair in all_pairs:
        # ดึงน้ำหนักคะแนนของเลขแต่ละตัว
        v1 = pos_votes.get(str(pair[0]), 0.0)
        v2 = pos_votes.get(str(pair[1]), 0.0)
        
        # นำน้ำหนักมารวมกัน เพื่อดูว่าคู่เลขนี้แข็งแกร่งแค่ไหน
        pair_weight_score = round(v1 + v2, 3)

        wr, profit = backtest_position(draws, pair, pos)
        
        # คัดเฉพาะตัวที่ผ่านเกณฑ์ P80 ของตำแหน่งนั้นๆ
        if wr >= p80_min:
            candidates.append({
                "pair": pair,
                "score": pair_weight_score,
                "win_rate": wr,
                "profit": profit
            })

    # เรียงลำดับ: เน้นน้ำหนักคะแนนนำ (เชื่อบอทตัวท็อป) ตามด้วยกำไร
    candidates.sort(key=lambda x: (x['score'], x['profit']), reverse=True)
    
    if not candidates:
        return None

    best = candidates[0]
    # คำนวณ Bet Size 0-100% ตามน้ำหนักคะแนน
    bet, status = calculate_weighted_bet(best['score'], best['win_rate'], p80_min)
    
    return {
        "pair": best['pair'],
        "win_rate": best['win_rate'],
        "profit": best['profit'],
        "bet_size": bet,
        "status": status,
        "score": best['score']
    }

def main():
    print("\n" + "🚀 [Core Optimizer] อัปเกรดระบบ: แยกสมรภูมิ + ชั่งน้ำหนักความเก่งบอท")
    
    with open(RISK_CONFIG, 'r', encoding='utf-8') as f:
        risk_data = json.load(f)

    try:
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            votes_data = json.load(f)
    except:
        votes_data = {}

    results = {"markets": {}}

    for market, config in risk_data['markets'].items():
        raw_file = os.path.join(DATA_DIR, f"raw_{market}.json")
        if not os.path.exists(raw_file): continue

        with open(raw_file, 'r', encoding='utf-8') as f:
            draws = json.load(f)

        print(f"🔎 วิเคราะห์ตลาด: {market.upper()}")

        # 🎯 ดึงข้อมูลโหวตเฉพาะตลาดนี้ส่งไปให้แม่ทัพ
        market_votes = votes_data.get(market, {})

        # รอบที่ 1: เฟ้นหาคู่เลขสมรภูมิ 'หน้า'
        best_f = hunt_best_pair(draws, market_votes, config['front']['min_winrate'], 'front')
        
        # รอบที่ 2: เฟ้นหาคู่เลขสมรภูมิ 'หลัง'
        best_b = hunt_best_pair(draws, market_votes, config['back']['min_winrate'], 'back')

        results["markets"][market] = {
            "front": best_f,
            "back": best_b,
            "last_update": "Sovereign-V3-Weights"
        }
        
        f_info = f"{best_f['pair']} ({best_f['bet_size']}%)" if best_f else "🔴 SKIP"
        b_info = f"{best_b['pair']} ({best_b['bet_size']}%)" if best_b else "🔴 SKIP"
        print(f"   [หน้า]: {f_info} | [หลัง]: {b_info}")

    with open(FINAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\n✅ อนุมัติงบเสร็จสิ้น! ข้อมูลพร้อมโชว์บน Dashboard แล้วครับ\n")

if __name__ == "__main__":
    main()
