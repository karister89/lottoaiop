import json
import os
import sys
import glob

# Import บอท 4 สาย (เวอร์ชัน V3 ที่แยกหน้า-หลังแล้ว)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sp_market, sp_stat, sp_math, sp_ai

# =====================================================================
# ⚙️ Configuration - Core Weight (V3 Split Position)
# =====================================================================
DATA_DIR = "../data/"
WEIGHTS_OUT = "../data/dynamic_weights.json"

def calculate_split_weights(draws, market_name):
    max_window = 100
    actual_window = min(max_window, len(draws) - 5) # เผื่อช่องว่างสำหรับตรวจผล
    
    if actual_window < 15: return None, None

    # เก็บประวัติการเข้าเป้าแยก หน้า (f) และ หลัง (b)
    bot_hits = {
        "market": {"f": [], "b": []},
        "stat":   {"f": [], "b": []},
        "math":   {"f": [], "b": []},
        "ai":     {"f": [], "b": []}
    }

    print(f"   🔎 กำลังประเมินผลแยกตำแหน่ง {actual_window} งวด...")

    for i in range(1, actual_window + 1):
        past_draws = draws[i:]
        actual_result = str(draws[i-1].get('twoTop', '')).zfill(2)
        if len(actual_result) != 2: continue
        
        target_f = actual_result[0] # ผลหลักสิบที่ออกจริง
        target_b = actual_result[1] # ผลหลักหน่วยที่ออกจริง
        
        # รันบอททุกตัวเพื่อเช็คว่า Top 5 ของแต่ละฝั่งเข้าไหม
        bots = {
            "market": sp_market.analyze_market_split(past_draws),
            "stat":   sp_stat.analyze_statistics_split(past_draws),
            "math":   sp_math.analyze_math_split(past_draws),
            "ai":     sp_ai.analyze_pattern_split(past_draws)
        }

        for name, (sc_f, sc_b) in bots.items():
            top5_f = [str(x) for x in sorted(range(10), key=lambda i: sc_f[i], reverse=True)[:5]]
            top5_b = [str(x) for x in sorted(range(10), key=lambda i: sc_b[i], reverse=True)[:5]]
            
            bot_hits[name]["f"].append(1 if target_f in top5_f else 0)
            bot_hits[name]["b"].append(1 if target_b in top5_b else 0)

    # คำนวณ Composite Win Rate แยก หน้า/หลัง
    final_weights = {"front": {}, "back": {}}
    performance_report = {}

    for pos in ["f", "b"]:
        pos_key = "front" if pos == "f" else "back"
        adjusted_scores = {}
        
        for bot_name in bot_hits:
            hits = bot_hits[bot_name][pos]
            # คำนวณ Win Rate 4 ระยะ
            wr15 = (sum(hits[:15])/15)*100
            wr100 = (sum(hits[:100])/len(hits))*100
            composite = (wr15 * 0.4) + (wr100 * 0.6) # เน้นความสด 40% ความเสถียร 60%
            
            # ปรับคะแนน (ถ้าเน่าเกินไปให้เป็น 0)
            adjusted_scores[bot_name] = composite if composite >= 20 else 0
            
            if bot_name not in performance_report: performance_report[bot_name] = {}
            performance_report[bot_name][pos_key] = round(composite, 1)

        # แปลงเป็นน้ำหนัก (Weight) รวมกันได้ 1.0
        total = sum(adjusted_scores.values())
        for bot_name, score in adjusted_scores.items():
            final_weights[pos_key][bot_name] = round(score/total, 4) if total > 0 else 0.25

    return final_weights, performance_report

def main():
    print("⏳ [Core Weight V3] เริ่มประเมินผลงานแยกสมรภูมิ...")
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    all_market_weights = {"markets": {}}

    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            draws = json.load(f)
        if not draws or len(draws) < 20: continue

        print(f"\n👨‍⚖️ วัดเกรดตลาด: {market_name.upper()}")
        weights, perf = calculate_split_weights(draws, market_name)
        
        if weights:
            all_market_weights["markets"][market_name] = {
                "weights": weights,
                "performance": perf
            }
    
    with open(WEIGHTS_OUT, 'w', encoding='utf-8') as f:
        json.dump(all_market_weights, f, indent=4)
    print(f"\n✅ อัปเกรดระบบ Weight แยกตำแหน่งสำเร็จ!")

if __name__ == "__main__":
    main()
