import json
import os
import sys
import glob

# Import บอท 4 สาย
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sp_market, sp_stat, sp_math, sp_ai

# =====================================================================
# ⚙️ Configuration - Core Weight (Ultimate Multi-Phase Edition)
# =====================================================================
DATA_DIR = "../data/"
WEIGHTS_OUT = "../data/dynamic_weights.json"

def calculate_ultimate_weights(draws, market_name):
    # ปรับเพดานสูงสุดที่ 100 วัน เพื่อรองรับบอทสายสถิติ (Stat/Math)
    max_window = 100
    actual_window = min(max_window, len(draws) - 1)
    
    if actual_window < 15:
        return None, None

    bot_hits = {"market": [], "stat": [], "math": [], "ai": []}

    print(f"   🔎 กำลังประเมินผลงานย้อนหลัง {actual_window} งวด (Deep Analysis)...")

    for i in range(1, actual_window + 1):
        past_draws = draws[i:]
        actual_result = str(draws[i-1].get('twoTop', '')).zfill(2)
        
        # รันบอทวิเคราะห์ทั้ง 4 ตัว
        def get_top2(scores):
            return [str(x[0]) for x in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:2]]

        bot_hits["market"].append(1 if any(d in actual_result for d in get_top2(sp_market.analyze_market(past_draws))) else 0)
        bot_hits["stat"].append(1 if any(d in actual_result for d in get_top2(sp_stat.analyze_statistics(past_draws))) else 0)
        bot_hits["math"].append(1 if any(d in actual_result for d in get_top2(sp_math.analyze_math(past_draws))) else 0)
        bot_hits["ai"].append(1 if any(d in actual_result for d in get_top2(sp_ai.analyze_pattern(past_draws))) else 0)

    # ======================================================
    # 🧮 คำนวณวินเรทแยกตาม 4 ระยะ (Phase Analysis)
    # ======================================================
    bot_status = {}
    adjusted_scores = {}
    
    for bot, hits in bot_hits.items():
        # คิด Win Rate แยกรายระยะ
        wr_15 = (sum(hits[:15]) / min(15, len(hits))) * 100 if len(hits) >= 1 else 0
        wr_30 = (sum(hits[:30]) / min(30, len(hits))) * 100 if len(hits) >= 1 else 0
        wr_60 = (sum(hits[:60]) / min(60, len(hits))) * 100 if len(hits) >= 1 else 0
        wr_100 = (sum(hits[:100]) / min(100, len(hits))) * 100 if len(hits) >= 1 else 0
        
        # 🌟 คะแนนสุทธิแบบถ่วงน้ำหนัก (Composite Win Rate)
        # ให้ความสำคัญกับความสด (15d) 30%, มาตรฐาน (30d/60d) 40%, และสถิติยาว (100d) 30%
        composite_wr = (wr_15 * 0.3) + (wr_30 * 0.2) + (wr_60 * 0.2) + (wr_100 * 0.3)
        
        # แจกเกรดสถานะบอท
        if composite_wr >= 40:
            status = "GREEN"
            adj = composite_wr
        elif composite_wr >= 20:
            status = "YELLOW"
            adj = composite_wr * 0.5 
        else:
            status = "RED"
            adj = 0           
            
        bot_status[bot] = {
            "wr_15d": round(wr_15, 1),
            "wr_30d": round(wr_30, 1),
            "wr_60d": round(wr_60, 1),
            "wr_100d": round(wr_100, 1),
            "composite_wr": round(composite_wr, 1),
            "status": status
        }
        adjusted_scores[bot] = adj

    # คำนวณส่วนแบ่งน้ำหนัก (Weight) ให้บอทแต่ละตัว
    total_adj = sum(adjusted_scores.values())
    weights = {k: round(v / total_adj, 4) if total_adj > 0 else 0.25 for k, v in adjusted_scores.items()}

    return weights, bot_status

def main():
    print("⏳ [Core Weight] เริ่มประเมินผลงาน 4 ระยะ (15/30/60/100 วัน)...")
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    all_market_weights = {"markets": {}}

    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            draws = json.load(f)

        if not draws or len(draws) < 15: continue

        print(f"\n👨‍⚖️ ตัดเกรดตลาด: {market_name.upper()}")
        weights, status = calculate_ultimate_weights(draws, market_name)
        
        if weights and status:
            all_market_weights["markets"][market_name] = {
                "weights": weights,
                "bot_performance": status
            }
            # แสดง Report สั้นๆ ใน GitHub Actions
            for b, s in status.items():
                print(f"   [{s['status']}] {b.upper()}: 15d:{s['wr_15d']}% | 100d:{s['wr_100d']}% | Avg:{s['composite_wr']}%")

    with open(WEIGHTS_OUT, 'w', encoding='utf-8') as f:
        json.dump(all_market_weights, f, ensure_ascii=False, indent=4)
    print(f"\n✅ [Core Weight] สรุปคะแนนสะสม 4 ระยะสำเร็จ!")

if __name__ == "__main__":
    main()
