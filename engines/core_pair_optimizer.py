import json
import os
import glob
from itertools import combinations

# =====================================================================
# ⚙️ Configuration - Core Optimizer (Sniper 40 Units - Consensus Edition)
# =====================================================================
DATA_DIR = "../data/"
WEIGHTS_FILE = "../data/dynamic_weights.json"
OPTIMIZED_OUT = "../data/optimized_pairs.json"
PAYOUT_RATE = 100.0
COST_PER_PAIR = 40.0  # ✅ แก้เป็น 40 บาท

def main():
    print("⏳ [Core Optimizer] กำลังไขว้คู่หา ROI สูงสุด (กลยุทธ์ 40 ชุด ไม่ตัดซ้ำ)...")
    
    weights_data = {}
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, 'r', encoding='utf-8') as f:
            weights_data = json.load(f).get("markets", {})

    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    if not raw_files:
        print("❌ ไม่พบไฟล์ข้อมูลดิบ!")
        return

    all_optimized_results = {"markets": {}}

    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)

            if not draws: continue

            print(f"\n🔮 รวบรวมผลโหวตตลาด: {market_name.upper()}")

            market_weights = weights_data.get(market_name, {}).get("weights", {
                "market": 0.25, "stat": 0.25, "math": 0.25, "ai": 0.25
            })

            total_scores = [0.0] * 10
            vote_counts = [0] * 10
            valid_bots = 0

            for bot in ["market", "stat", "math", "ai"]:
                bot_file = os.path.join(DATA_DIR, f"result_{bot}_{market_name}.json")
                if os.path.exists(bot_file):
                    with open(bot_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        weight = market_weights.get(bot, 0)
                        if weight > 0:
                            valid_bots += 1
                            for i in range(10): total_scores[i] += data["raw_scores"][i] * weight
                            top_3 = data.get("top_digits", [])[:3]
                            for digit in top_3:
                                if str(digit).isdigit(): vote_counts[int(digit)] += 1

            ranked = sorted([(str(i), vote_counts[i], total_scores[i]) for i in range(10)], 
                            key=lambda x: (x[1], x[2]), reverse=True)
            top_5 = [r[0] for r in ranked[:5]]
            
            highest_vote = ranked[0][1]
            is_consensus_broken = (highest_vote < 2 and valid_bots >= 3)

            candidate_pairs = list(combinations(top_5, 2))
            best_res = {"pair": None, "profit": -9999, "win_rate": 0, "miss_latest": True, "wins": 0, "consensus_broken": is_consensus_broken}
            
            # 🔻 จุดที่แก้: ลอจิกการตรวจรางวัลแบบแยกหลัก (ไม่ตัดซ้ำ) 🔻
            for pair in candidate_pairs:
                profit, wins, miss_latest = 0, 0, False
                for i, row in enumerate(draws[:30]):
                    num = str(row.get('twoTop', '')).zfill(2)
                    if not num.isdigit(): continue
                    
                    hits = 0
                    # เช็คเลขตัวที่ 1 ในหลักสิบ/หลักหน่วย
                    if pair[0] == num[0]: hits += 1
                    if pair[0] == num[1]: hits += 1
                    # เช็คเลขตัวที่ 2 ในหลักสิบ/หลักหน่วย
                    if pair[1] == num[0]: hits += 1
                    if pair[1] == num[1]: hits += 1
                    
                    if hits > 0:
                        wins += 1
                        profit += (hits * PAYOUT_RATE) - COST_PER_PAIR
                    else:
                        profit -= COST_PER_PAIR
                        if i == 0: miss_latest = True 
                
                if profit > best_res["profit"]:
                    best_res = {
                        "pair": pair, "profit": profit, "win_rate": round((wins/30)*100, 2), 
                        "miss_latest": miss_latest, "wins": wins, "consensus_broken": is_consensus_broken
                    }

            if best_res["pair"]:
                all_optimized_results["markets"][market_name] = best_res
                print(f"   🎯 คู่เด็ด: {best_res['pair']} | โหวต: {highest_vote} | กำไรจำลอง: {best_res['profit']} ฿")

        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

    with open(OPTIMIZED_OUT, 'w', encoding='utf-8') as f:
        json.dump(all_optimized_results, f, ensure_ascii=False, indent=4)
    print(f"\n✅ [Core Optimizer] บันทึกคู่เลขเด็ด 40 ชุดเรียบร้อย!")

if __name__ == "__main__":
    main()
