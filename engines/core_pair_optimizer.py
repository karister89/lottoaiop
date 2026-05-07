import json
import os
from itertools import combinations

# Configuration
RAW_DATA_FILE = "../data/raw_excel.json"
WEIGHTS_FILE = "../data/dynamic_weights.json"
RESULTS_PATH = "../data/result_{}.json"
OPTIMIZED_OUT = "../data/optimized_pairs.json"
PAYOUT_RATE = 90.0
COST_PER_PAIR = 38.0

def main():
    print("⏳ [Core Optimizer] กำลังไขว้คู่หา ROI สูงสุด...")
    # โหลดข้อมูลและน้ำหนัก
    with open(RAW_DATA_FILE, 'r') as f: draws = json.load(f)
    with open(WEIGHTS_FILE, 'r') as f: weights = json.load(f)["weights"]
    
    # รวมคะแนนจากบอท 4 สาย
    total_scores = [0.0] * 10
    for bot in ["market", "stat", "math", "ai"]:
        bot_file = RESULTS_PATH.format(bot)
        if os.path.exists(bot_file):
            with open(bot_file, 'r') as f:
                data = json.load(f)
                for i in range(10): total_scores[i] += data["raw_scores"][i] * weights[bot]

    ranked = sorted([(str(i), s) for i, s in enumerate(total_scores)], key=lambda x: x[1], reverse=True)
    top_5 = [r[0] for r in ranked[:5]]
    candidate_pairs = list(combinations(top_5, 2))
    
    best_res = {"pair": None, "profit": -9999, "win_rate": 0, "miss_latest": True}
    
    for pair in candidate_pairs:
        profit, wins, miss_latest = 0, 0, False
        for i, row in enumerate(draws[:30]):
            num = str(row.get('twoTop', '')).zfill(2)
            hits = (1 if pair[0] in num else 0) + (1 if pair[1] in num else 0)
            if hits > 0:
                wins += 1
                profit += (hits * PAYOUT_RATE) - COST_PER_PAIR
            else:
                profit -= COST_PER_PAIR
                if i == 0: miss_latest = True
        
        if profit > best_res["profit"]:
            best_res = {"pair": pair, "profit": profit, "win_rate": (wins/30)*100, "miss_latest": miss_latest, "wins": wins}

    with open(OPTIMIZED_OUT, 'w', encoding='utf-8') as f:
        json.dump(best_res, f, ensure_ascii=False, indent=4)
    print(f"✅ [Core Optimizer] คู่ที่ทำกำไรสูงสุดคือ {best_res['pair']} (Profit: {best_res['profit']})")

if __name__ == "__main__": main()
