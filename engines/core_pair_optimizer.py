import json
import os
import glob
import numpy as np
from itertools import combinations

# =====================================================================
# ⚖️ Configuration - Optimizer (V3 Smooth & Streak Guard Edition)
# =====================================================================
DATA_DIR = "data"
RISK_CONFIG = os.path.join(DATA_DIR, "risk_config.json")
VOTES_FILE = os.path.join(DATA_DIR, "bot_consensus_votes.json")
FINAL_OUTPUT = os.path.join(DATA_DIR, "optimized_pairs.json")

def check_streak_and_trend(draws, pair, position):
    """ตรวจสอบการแพ้ติดกัน (Streak) และแนวโน้มกำไร (Profit Trend)"""
    p0, p1 = str(pair[0]), str(pair[1])
    test_draws = draws[:30] # เช็คย้อนหลัง 30 งวด
    
    losses = 0
    consecutive_losses = 0
    streak_broken = False
    total_profit = 0
    
    for i, row in enumerate(test_draws):
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
        
        target = num[0] if position == 'front' else num[1]
        is_win = (p0 == target or p1 == target)
        
        # คำนวณกำไรสะสม (ทุน 20 จ่าย 100)
        total_profit += 80 if is_win else -20
        
        # นับการแพ้ติดกันจากงวดล่าสุด (Index 0)
        if not is_win and not streak_broken:
            consecutive_losses += 1
        else:
            streak_broken = True
            
    return consecutive_losses, total_profit

def calculate_weighted_bet(pair_weight_score, current_wr, p80_value, streak, trend_profit):
    """สูตรคำนวณเงินเดิมพันแบบคัดกรองความเสี่ยง (Streak & Trend Filter)"""
    
    # 1. ระบบเบรกฉุกเฉิน: แพ้ติดกันเกิน 3 งวด หรือกำไร 30 งวดล่าสุดติดลบ ให้หยุดทันที
    if streak >= 3 or trend_profit < 0:
        return 0, "🔴 RED (Bad Streak/Trend)"
    
    # 2. ตัวกรองนิรภัยเดิม: วินเรทต้องผ่านเกณฑ์ P80
    if current_wr < p80_value:
        return 0, "🔴 RED (Low WR)"
    
    # 3. พิจารณาจากคะแนนความมั่นใจและประวัติ
    if pair_weight_score >= 1.20 and streak == 0:
        bet_size = 100
        status = "🟢 GREEN"
    elif pair_weight_score >= 0.80 and streak <= 1:
        bet_size = 80
        status = "🟡 YELLOW"
    elif pair_weight_score >= 0.40 and streak <= 2:
        bet_size = 50 
        status = "🟡 YELLOW"
    else:
        bet_size = 0
        status = "🔴 RED"
        
    return bet_size, status

def backtest_position(draws, pair, position='front'):
    """จำลองการแทงย้อนหลัง 30 งวด เพื่อหาวินเรท"""
    wins = 0
    p0, p1 = str(pair[0]), str(pair[1])
    test_draws = draws[:30]
    
    for row in test_draws:
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
        target = num[0] if position == 'front' else num[1]
        if p0 == target or p1 == target:
            wins += 1
            
    win_rate = (wins / len(test_draws)) * 100 if len(test_draws) > 0 else 0
    return win_rate

def hunt_best_pair(draws, market_votes, p80_min, pos='front'):
    """คัดเลือกคู่เลขที่ผ่านทั้งเกณฑ์คะแนนและเกณฑ์ความเสี่ยง"""
    all_pairs = list(combinations(range(10), 2))
    candidates = []
    pos_votes = market_votes.get(pos, {})

    for pair in all_pairs:
        v1 = pos_votes.get(str(pair[0]), 0.0)
        v2 = pos_votes.get(str(pair[1]), 0.0)
        pair_weight_score = round(v1 + v2, 3)

        wr = backtest_position(draws, pair, pos)
        streak, trend_p = check_streak_and_trend(draws, pair, pos)
        
        if wr >= p80_min:
            candidates.append({
                "pair": pair,
                "score": pair_weight_score,
                "win_rate": wr,
                "streak": streak,
                "trend_profit": trend_p
            })

    # เรียงลำดับ: เน้นที่คะแนนรวมและความเสี่ยงต่ำ (Trend Profit)
    candidates.sort(key=lambda x: (x['trend_profit'], x['score']), reverse=True)
    
    if not candidates:
        return None

    best = candidates[0]
    bet, status = calculate_weighted_bet(
        best['score'], 
        best['win_rate'], 
        p80_min, 
        best['streak'], 
        best['trend_profit']
    )
    
    return {
        "pair": best['pair'],
        "win_rate": best['win_rate'],
        "profit_30d": best['trend_profit'],
        "streak": best['streak'],
        "bet_size": bet,
        "status": status,
        "score": best['score']
    }

def main():
    print("\n" + "🚀 [Core Optimizer] อัปเกรดระบบ: เพิ่มเกราะป้องกันการแพ้ติดกัน (Streak Guard)")
    
    try:
        with open(RISK_CONFIG, 'r', encoding='utf-8') as f:
            risk_data = json.load(f)
        with open(VOTES_FILE, 'r', encoding='utf-8') as f:
            votes_data = json.load(f)
    except Exception as e:
        print(f"❌ Error Loading Config: {e}")
        return

    results = {"markets": {}}

    for market, config in risk_data['markets'].items():
        raw_file = os.path.join(DATA_DIR, f"raw_{market}.json")
        if not os.path.exists(raw_file): continue

        with open(raw_file, 'r', encoding='utf-8') as f:
            draws = json.load(f)

        print(f"🔎 วิเคราะห์ตลาด: {market.upper()}")
        market_votes = votes_data.get(market, {})

        best_f = hunt_best_pair(draws, market_votes, config['front']['min_winrate'], 'front')
        best_b = hunt_best_pair(draws, market_votes, config['back']['min_winrate'], 'back')

        results["markets"][market] = {
            "front": best_f,
            "back": best_b,
            "last_update": "V3-Streak-Guard"
        }
        
        f_info = f"{best_f['pair']} (Bet: {best_f['bet_size']}% | Streak: {best_f['streak']})" if best_f and best_f['bet_size'] > 0 else "🔴 SKIP"
        b_info = f"{best_b['pair']} (Bet: {best_b['bet_size']}% | Streak: {best_b['streak']})" if best_b and best_b['bet_size'] > 0 else "🔴 SKIP"
        print(f"   [หน้า]: {f_info}")
        print(f"   [หลัง]: {b_info}")

    with open(FINAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\n✅ อนุมัติงบและคัดกรองความเสี่ยงเสร็จสิ้น!\n")

if __name__ == "__main__":
    main()
