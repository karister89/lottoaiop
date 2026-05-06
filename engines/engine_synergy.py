import json
import os
import sys

# โหลดโมดูลของบอททั้ง 4 ตัวเข้ามา เพื่อสั่งให้มันทำข้อสอบย้อนหลัง
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sp_market
import sp_stat
import sp_math
import sp_ai

# =====================================================================
# ⚙️ DATA PATH CONFIGURATION (ระบบหาไฟล์อัตโนมัติ)
# =====================================================================
DATA_DIR = "../data/"
RAW_DATA_FILE = "../data/raw_excel.json"
RISK_CONFIG_FILE = "../data/risk_config.json"
OUTPUT_FILE = "../data/final_synergy.json"

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# =====================================================================
# 🧠 ฟังก์ชันคำนวณน้ำหนักอัตโนมัติ (Adaptive Weighting)
# =====================================================================
def calculate_dynamic_weights(draws, window):
    print("⏳ [Adaptive Synergy] กำลังจับบอท 4 สายทำข้อสอบย้อนหลัง เพื่อหาน้ำหนักที่ดีที่สุด...")
    bot_wins = {"market": 0, "stat": 0, "math": 0, "ai": 0}
    
    for i in range(1, window + 1):
        if i >= len(draws) - 2: break # ป้องกันข้อมูลหมด
        
        past_draws = draws[i:] # ตัดข้อมูลมาให้เหมือน "วันนั้นในอดีต"
        actual_result = str(draws[i-1].get('twoTop', '')).zfill(2) # เฉลยของวันถัดมา
        
        # 1. Market Test
        m_scores = sp_market.analyze_market(past_draws)
        m_top = sorted([(str(idx), s) for idx, s in enumerate(m_scores)], key=lambda x: x[1], reverse=True)[:2]
        if m_top[0][0] in actual_result or m_top[1][0] in actual_result: bot_wins["market"] += 1
            
        # 2. Stat Test
        s_scores = sp_stat.analyze_statistics(past_draws)
        s_top = sorted([(str(idx), s) for idx, s in enumerate(s_scores)], key=lambda x: x[1], reverse=True)[:2]
        if s_top[0][0] in actual_result or s_top[1][0] in actual_result: bot_wins["stat"] += 1
            
        # 3. Math Test
        mt_scores = sp_math.analyze_math(past_draws)
        mt_top = sorted([(str(idx), s) for idx, s in enumerate(mt_scores)], key=lambda x: x[1], reverse=True)[:2]
        if mt_top[0][0] in actual_result or mt_top[1][0] in actual_result: bot_wins["math"] += 1
            
        # 4. AI Test
        a_scores = sp_ai.analyze_pattern(past_draws)
        a_top = sorted([(str(idx), s) for idx, s in enumerate(a_scores)], key=lambda x: x[1], reverse=True)[:2]
        if a_top[0][0] in actual_result or a_top[1][0] in actual_result: bot_wins["ai"] += 1

    total_wins = sum(bot_wins.values())
    
    # คำนวณออกมาเป็นสัดส่วนน้ำหนัก (Weighting)
    if total_wins == 0:
        weights = {"market": 0.25, "stat": 0.25, "math": 0.25, "ai": 0.25}
    else:
        weights = {k: round(v / total_wins, 4) for k, v in bot_wins.items()}
        
    print(f"📊 ผลทดสอบบอท 30 วันล่าสุด: Market({bot_wins['market']} win), Stat({bot_wins['stat']} win), Math({bot_wins['math']} win), AI({bot_wins['ai']} win)")
    return weights, bot_wins

# =====================================================================
# 🧠 ฟังก์ชันทดสอบหา Win Rate ของคู่เลขที่ได้ (Risk Backtest)
# =====================================================================
def backtest_pair(pair, draws, window, min_winrate):
    if not draws: return 0.0, "⚪ UNKNOWN", 0
    wins = 0
    miss_latest = False
    test_draws = draws[:window] 
    
    for i, row in enumerate(test_draws):
        num_str = str(row.get('twoTop', '')).zfill(2)
        if str(pair[0]) in num_str or str(pair[1]) in num_str:
            wins += 1
        else:
            if i == 0: miss_latest = True
                
    win_rate = (wins / len(test_draws)) * 100
    if win_rate < min_winrate: status = f"🔴 RED (ต่ำกว่าเกณฑ์ตลาดที่ {min_winrate}%)"
    elif miss_latest: status = "🟡 YELLOW (วินเรทผ่าน แต่งวดล่าสุดเพิ่งหลุด หรือเริ่มมีอาการแกว่ง)"
    else: status = "🟢 GREEN (เดินดี วินเรทสูง ปลอดภัย)"
    return win_rate, status, wins

# =====================================================================
# 🚀 CORE ENGINE
# =====================================================================
def main():
    raw_draws = load_json("raw_excel.json")
    if not raw_draws:
        print("❌ Error: ไม่พบไฟล์ข้อมูล raw_excel.json")
        return

    # โหลดค่าเกณฑ์ความเสี่ยงแบบ P80 (Pure Math) จาก Risk Tuner
    risk_config = load_json("risk_config.json")
    WINDOW = risk_config.get("backtest_window", 30) if risk_config else 30
    MIN_WINRATE = risk_config.get("dynamic_min_winrate", 70.0) if risk_config else 70.0

    print(f"\n🧠 เริ่มเดินเครื่อง Sovereign Synergy Engine (Dynamic Threshold: {MIN_WINRATE}%)...")

    # 1. ให้ดาต้าตัดสินน้ำหนักเอง (Adaptive Weighting)
    dynamic_weights, bot_wins_history = calculate_dynamic_weights(raw_draws, WINDOW)
    print(f"⚖️ น้ำหนักล่าสุดที่ดาต้าตัดสินให้: {dynamic_weights}\n")

    # 2. โหลดคะแนนดิบของงวดปัจจุบัน แล้วคูณด้วยน้ำหนักที่ได้มาสดๆ ร้อนๆ
    market_data = load_json("result_market.json")
    stat_data   = load_json("result_stat.json")
    math_data   = load_json("result_math.json")
    ai_data     = load_json("result_ai.json")
    
    total_scores = [0.0] * 10
    def apply_scores(bot_data, weight):
        if bot_data and "raw_scores" in bot_data:
            for i in range(10): total_scores[i] += bot_data["raw_scores"][i] * weight

    apply_scores(market_data, dynamic_weights["market"])
    apply_scores(stat_data, dynamic_weights["stat"])
    apply_scores(math_data, dynamic_weights["math"])
    apply_scores(ai_data, dynamic_weights["ai"])
    
    # 3. จัดอันดับตัวเลข
    ranked_digits = sorted([(str(i), s) for i, s in enumerate(total_scores)], key=lambda x: x[1], reverse=True)
    
    # 4. ทดสอบหา "แร้ง OP"
    candidate_pairs = [
        ([ranked_digits[0][0], ranked_digits[1][0]], "Primary 1&2"),
        ([ranked_digits[0][0], ranked_digits[2][0]], "Alternate 1&3"),
        ([ranked_digits[1][0], ranked_digits[2][0]], "Alternate 2&3")
    ]
    
    op_pair, op_win_rate, op_status, op_wins = None, 0.0, "", 0
    for pair, desc in candidate_pairs:
        win_rate, status, wins = backtest_pair(pair, raw_draws, WINDOW, MIN_WINRATE)
        if "RED" not in status:
            op_pair, op_win_rate, op_status, op_wins = pair, win_rate, status, wins
            print(f"✅ ค้นพบแร้ง OP ที่เสถียร: คู่ {op_pair} ({desc})")
            break
            
    if op_pair is None:
        op_pair = candidate_pairs[0][0]
        op_win_rate, op_status, op_wins = backtest_pair(op_pair, raw_draws, WINDOW, MIN_WINRATE)
        print("⚠️ Warning: สภาวะตลาดผันผวนสูง ทุกคู่ติดสถานะ RED")

    support_digit = ranked_digits[3][0] if op_pair == candidate_pairs[0][0] else ranked_digits[1][0]
    
    # 5. สรุปผล
    final_result = {
        "system_status": "Sovereign V3 Online (100% Data-Driven)",
        "op_pair": op_pair,
        "support_digit": support_digit,
        "risk_management": {
            "win_rate_percent": round(op_win_rate, 2),
            "wins": op_wins,
            "dynamic_threshold": MIN_WINRATE,
            "status": op_status
        },
        "bot_performance_30_days": bot_wins_history,
        "weights_used": dynamic_weights
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=4)
        
    print(f"\n📊 --- สรุปผลลัพธ์ (Sovereign V3 Report) ---")
    print(f"🎯 แร้ง OP (ตัวหลัก): {op_pair}")
    print(f"🛡️ เลขรอง (Support): {support_digit}")
    print(f"📈 Win Rate: {round(op_win_rate, 2)}% ({op_wins}/{WINDOW} งวดล่าสุด)")
    print(f"🚦 สถานะความเสี่ยง: {op_status}")
    print(f"📁 บันทึกผลลัพธ์ที่: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
