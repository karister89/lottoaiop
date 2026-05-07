import json
import os
import glob
from itertools import combinations

# =====================================================================
# ⚙️ Configuration - Core Optimizer (Consensus Edition)
# =====================================================================
DATA_DIR = "../data/"
WEIGHTS_FILE = "../data/dynamic_weights.json"
OPTIMIZED_OUT = "../data/optimized_pairs.json"
PAYOUT_RATE = 100.0
COST_PER_PAIR = 40.0

def main():
    print("⏳ [Core Optimizer] กำลังไขว้คู่หา ROI สูงสุดด้วยระบบโหวตเอกฉันท์ (Consensus)...")
    
    # โหลดสมุดพกกรรมการ (น้ำหนักของแต่ละบอทในแต่ละตลาด)
    weights_data = {}
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, 'r', encoding='utf-8') as f:
            weights_data = json.load(f).get("markets", {})
    else:
        print("⚠️ ไม่พบไฟล์ dynamic_weights.json (ระบบจะใช้น้ำหนัก 0.25 เท่ากันหมด)")

    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    if not raw_files:
        print("❌ ไม่พบไฟล์ข้อมูลดิบ (raw_*.json)!")
        return

    # กล่องเก็บผลลัพธ์ของทุกตลาดรวมกัน
    all_optimized_results = {"markets": {}}

    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)

            if not draws or len(draws) == 0: continue

            print(f"\n🔮 กำลังรวบรวมผลโหวตตลาด: {market_name.upper()}")

            market_weights = weights_data.get(market_name, {}).get("weights", {
                "market": 0.25, "stat": 0.25, "math": 0.25, "ai": 0.25
            })

            total_scores = [0.0] * 10
            vote_counts = [0] * 10  # 🔻 กล่องเก็บผลโหวตของบอท 🔻
            valid_bots = 0

            for bot in ["market", "stat", "math", "ai"]:
                bot_file = os.path.join(DATA_DIR, f"result_{bot}_{market_name}.json")
                if os.path.exists(bot_file):
                    with open(bot_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        weight = market_weights.get(bot, 0)
                        
                        # ให้สิทธิ์โหวตเฉพาะบอทที่ไม่ได้โดนใบแดง (weight > 0)
                        if weight > 0:
                            valid_bots += 1
                            
                            # 1. รวมคะแนนดิบ (เอาไว้ใช้เป็นเกณฑ์ตัดสินเวลาโหวตเท่ากัน)
                            for i in range(10): 
                                total_scores[i] += data["raw_scores"][i] * weight
                            
                            # 2. นับโหวต: ดึงเลข Top 3 ของบอทตัวนี้มาบวกคะแนนโหวต +1
                            top_3_of_bot = data.get("top_digits", [])[:3]
                            for digit_str in top_3_of_bot:
                                if digit_str.isdigit():
                                    vote_counts[int(digit_str)] += 1

            # 🔻 ตัดสินด้วย Consensus: เรียงลำดับตาม 'จำนวนโหวต' เป็นหลัก, ถ้าโหวตเท่ากันค่อยดู 'คะแนนดิบ'
            ranked = sorted([(str(i), vote_counts[i], total_scores[i]) for i in range(10)], 
                            key=lambda x: (x[1], x[2]), reverse=True)
            
            # ดึง 5 อันดับแรกมาจับคู่
            top_5 = [r[0] for r in ranked[:5]]
            
            # เช็คเสียงแตก: ถ้าเลขอันดับ 1 ยังได้โหวตแค่ 1 เสียง แสดงว่าบอทตีกันเองหนักมาก
            highest_vote = ranked[0][1]
            is_consensus_broken = False
            if highest_vote < 2 and valid_bots >= 3:
                print("   ⚠️ บอทเสียงแตก! (ไม่มีเลขไหนได้เกิน 1 โหวต) ความแม่นยำอาจลดลง")
                is_consensus_broken = True

            candidate_pairs = list(combinations(top_5, 2))
            best_res = {"pair": None, "profit": -9999, "win_rate": 0, "miss_latest": True, "wins": 0, "consensus_broken": is_consensus_broken}
            
            # จำลองการลงทุน (Backtest) 30 งวดล่าสุด
            for pair in candidate_pairs:
                profit, wins, miss_latest = 0, 0, False
                for i, row in enumerate(draws[:30]):
                    num = str(row.get('twoTop', '')).zfill(2)
                    if not num: continue
                    
                    hits = (1 if pair[0] in num else 0) + (1 if pair[1] in num else 0)
                    if hits > 0:
                        wins += 1
                        profit += (hits * PAYOUT_RATE) - COST_PER_PAIR
                    else:
                        profit -= COST_PER_PAIR
                        if i == 0: miss_latest = True # งวดล่าสุดเพิ่งพลาดมา
                
                if profit > best_res["profit"]:
                    best_res = {
                        "pair": pair, 
                        "profit": profit, 
                        "win_rate": round((wins/30)*100, 2), 
                        "miss_latest": miss_latest, 
                        "wins": wins,
                        "consensus_broken": is_consensus_broken
                    }

            if best_res["pair"]:
                all_optimized_results["markets"][market_name] = best_res
                print(f"   🎯 คู่ที่ดีที่สุด: {best_res['pair']} | โหวตสูงสุด: {highest_vote}/{valid_bots} เสียง | Win Rate: {best_res['win_rate']}%")

        except Exception as e:
            print(f"❌ Error ตลาด {market_name}: {e}")

    # บันทึกไฟล์รวมเก็บคู่เลขของทุกตลาด ส่งให้บอสใหญ่ (Money Commander)
    with open(OPTIMIZED_OUT, 'w', encoding='utf-8') as f:
        json.dump(all_optimized_results, f, ensure_ascii=False, indent=4)
    print(f"\n✅ [Core Optimizer] บันทึกคู่เลขเด็ดด้วยระบบโหวตเอกฉันท์สำเร็จ!")

if __name__ == "__main__":
    main()
