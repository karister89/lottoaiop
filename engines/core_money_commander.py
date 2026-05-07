import json
import os

OPTIMIZED_FILE = "../data/optimized_pairs.json"
RISK_CONFIG = "../data/risk_config.json"
FINAL_OUT = "../data/final_synergy.json"

def main():
    print("⏳ [Core Money] คำนวณแผนการลงทุนแบบ Dynamic...")
    with open(OPTIMIZED_FILE, 'r') as f: opt = json.load(f)
    with open(RISK_CONFIG, 'r') as f: risk = json.load(f)
    
    min_wr = risk.get("dynamic_min_winrate", 70.0)
    conf = 100
    
    # คำนวณ % ตามหลักการที่พี่นพพลต้องการ
    if opt["profit"] <= 0: conf -= 50
    if opt["win_rate"] < min_wr: conf -= ((min_wr - opt["win_rate"]) * 2)
    if opt["miss_latest"]: conf -= 40
    
    bet_size = max(0, (int(conf) // 10) * 10)
    
    status = "🟢 GREEN" if bet_size >= 80 else "🟡 YELLOW" if bet_size >= 40 else "🔴 RED"
    
    final = {
        "report": f"Sovereign V3 - {status}",
        "pair": opt["pair"],
        "bet_size": f"{bet_size}%",
        "details": {
            "30d_profit": opt["profit"],
            "win_rate": f"{round(opt['win_rate'], 2)}%",
            "market_threshold": f"{min_wr}%"
        }
    }
    
    with open(FINAL_OUT, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=4)
    print(f"🎯 [Core Money] สรุปผล: {opt['pair']} | ลงเงิน: {bet_size}% | สถานะ: {status}")

if __name__ == "__main__": main()
