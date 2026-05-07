import json
import os
import sys

# Import บอท 4 สายเข้ามาวัดผล
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sp_market, sp_stat, sp_math, sp_ai

# Configuration
RAW_DATA_FILE = "../data/raw_excel.json"
RISK_CONFIG_FILE = "../data/risk_config.json"
WEIGHTS_OUT = "../data/dynamic_weights.json"

def calculate_dynamic_weights(draws, window):
    print(f"⏳ [Core Weight] ประเมินฟอร์มบอท 4 สายย้อนหลัง {window} งวด...")
    bot_wins = {"market": 0, "stat": 0, "math": 0, "ai": 0}
    
    for i in range(1, window + 1):
        if i >= len(draws) - 2: break
        past_draws = draws[i:]
        actual_result = str(draws[i-1].get('twoTop', '')).zfill(2)
        
        # Test Each Specialist
        if any(d in actual_result for d in [str(idx) for idx, s in enumerate(sp_market.analyze_market(past_draws)) if s == max(sp_market.analyze_market(past_draws))][:2]): bot_wins["market"] += 1
        if any(d in actual_result for d in [str(idx) for idx, s in enumerate(sp_stat.analyze_statistics(past_draws)) if s == max(sp_stat.analyze_statistics(past_draws))][:2]): bot_wins["stat"] += 1
        if any(d in actual_result for d in [str(idx) for idx, s in enumerate(sp_math.analyze_math(past_draws)) if s == max(sp_math.analyze_math(past_draws))][:2]): bot_wins["math"] += 1
        if any(d in actual_result for d in [str(idx) for idx, s in enumerate(sp_ai.analyze_pattern(past_draws)) if s == max(sp_ai.analyze_pattern(past_draws))][:2]): bot_wins["ai"] += 1

    total_wins = sum(bot_wins.values())
    weights = {k: round(v / total_wins, 4) if total_wins > 0 else 0.25 for k, v in bot_wins.items()}
    return weights, bot_wins

def main():
    if not os.path.exists(RAW_DATA_FILE): return
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f: draws = json.load(f)
    
    # ดึงค่า Window จาก Risk Config
    window = 30
    if os.path.exists(RISK_CONFIG_FILE):
        with open(RISK_CONFIG_FILE, 'r') as f: window = json.load(f).get("backtest_window", 30)

    weights, history = calculate_dynamic_weights(draws, window)
    
    output = {"weights": weights, "bot_performance": history}
    with open(WEIGHTS_OUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"✅ [Core Weight] บันทึกน้ำหนักใหม่: {weights}")

if __name__ == "__main__": main()
