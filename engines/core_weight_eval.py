import json
import os
import sys
import glob

# Import บอท 4 สายเข้ามาวัดผล
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sp_market, sp_stat, sp_math, sp_ai

# =====================================================================
# ⚙️ Configuration - Core Weight (Multi-Market Edition)
# =====================================================================
DATA_DIR = "../data/"
WEIGHTS_OUT = "../data/dynamic_weights.json"

def calculate_dynamic_weights(draws, window, market_name):
    bot_wins = {"market": 0, "stat": 0, "math": 0, "ai": 0}
    
    actual_window = min(window, len(draws) - 1)
    if actual_window < 1:
        return None, None

    for i in range(1, actual_window + 1):
        past_draws = draws[i:]
        actual_result = str(draws[i-1].get('twoTop', '')).zfill(2)
        
        # ⚡ ปรับสปีด: เรียกบอทให้คำนวณแค่ครั้งเดียวต่องวด
        scores_mkt = sp_market.analyze_market(past_draws)
        scores_stat = sp_stat.analyze_statistics(past_draws)
        scores_math = sp_math.analyze_math(past_draws)
        scores_ai = sp_ai.analyze_pattern(past_draws)
        
        # ดึงเลข Top 2 ของแต่ละบอทออกมา
        top_mkt = [str(x[0]) for x in sorted(enumerate(scores_mkt), key=lambda x: x[1], reverse=True)[:2]]
        top_stat = [str(x[0]) for x in sorted(enumerate(scores_stat), key=lambda x: x[1], reverse=True)[:2]]
        top_math = [str(x[0]) for x in sorted(enumerate(scores_math), key=lambda x: x[1], reverse=True)[:2]]
        top_ai = [str(x[0]) for x in sorted(enumerate(scores_ai), key=lambda x: x[1], reverse=True)[:2]]
        
        # ตรวจคำตอบว่าทายถูกไหม (ถ้ารูดหน้า/หลังเข้า 1 ใน 2 ตัว ถือว่า Win)
        if any(d in actual_result for d in top_mkt): bot_wins["market"] += 1
        if any(d in actual_result for d in top_stat): bot_wins["stat"] += 1
        if any(d in actual_result for d in top_math): bot_wins["math"] += 1
        if any(d in actual_result for d in top_ai): bot_wins["ai"] += 1

    # ======================================================
    # 🟨 ระบบแจกใบเหลือง / ใบแดง (Penalty System)
    # ======================================================
    bot_status = {}
    adjusted_scores = {}
    
    for bot, wins in bot_wins.items():
        wr = (wins / actual_window) * 100
        
        # โอกาสสุ่มเดาเลข 2 ตัวถูกคือ 20% ดังนั้นต้องทำได้ดีกว่านี้
        if wr >= 40:
            status = "GREEN"  # ท็อปฟอร์ม
            adj = wins        # ได้น้ำหนักเต็ม 100%
        elif wr >= 20:
            status = "YELLOW" # ฟอร์มตก (ใบเหลือง)
            adj = wins * 0.5  # ⚠️ โดนหั่นความน่าเชื่อถือลงครึ่งนึง!
        else:
            status = "RED"    # ฟอร์มแย่กว่าหลับตาแทง (ใบแดง)
            adj = 0           # 🛑 แบน! ไม่ให้ค่าน้ำหนักเลย
            
        bot_status[bot] = {
            "wins": wins,
            "win_rate": round(wr, 1),
            "status": status
        }
        adjusted_scores[bot] = adj

    # คำนวณเปอร์เซ็นต์น้ำหนักสุดท้าย (Weight)
    total_adj = sum(adjusted_scores.values())
    if total_adj > 0:
        weights = {k: round(v / total_adj, 4) for k, v in adjusted_scores.items()}
    else:
        # กรณีวิกฤต: โดนใบแดงยกแก๊ง (แจกน้ำหนักเท่ากันไปก่อน)
        weights = {k: 0.25 for k in bot_wins.keys()}

    return weights, bot_status

def main():
    print("⏳ [Core Weight] เริ่มประเมินผลงานบอทย้อนหลัง (Multi-Market)...")
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    if not raw_files:
        print("❌ ไม่พบไฟล์ข้อมูลดิบ (raw_*.json)!")
        return

    all_market_weights = {"markets": {}}
    window = 30 # งวดที่ใช้ประเมินย้อนหลัง

    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
            
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        print(f"\n👨‍⚖️ กำลังตัดเกรดบอทในตลาด: {market_name.upper()}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            draws = json.load(f)

        if not draws: continue

        weights, status = calculate_dynamic_weights(draws, window, market_name)
        
        if weights and status:
            all_market_weights["markets"][market_name] = {
                "weights": weights,
                "bot_performance": status
            }
            
            # โชว์ผลลัพธ์การแจกใบเหลือง/ใบแดงให้ดูสดๆ
            for b, s in status.items():
                card = "🟩" if s['status'] == "GREEN" else "🟨" if s['status'] == "YELLOW" else "🟥"
                print(f"   {card} {b.upper()}: Win {s['win_rate']}% -> ได้น้ำหนัก {weights[b]*100}%")

    # บันทึกสมุดพกรวมทุกตลาดส่งให้กุนซือคนที่ 2
    with open(WEIGHTS_OUT, 'w', encoding='utf-8') as f:
        json.dump(all_market_weights, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ [Core Weight] บันทึกสมุดพกกรรมการครบทุกตลาดแล้ว!")

if __name__ == "__main__":
    main()
