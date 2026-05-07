import json
import os

# =====================================================================
# ⚙️ Configuration - Core Money Commander (Sniper & Double-Dip Mode)
# =====================================================================
DATA_DIR = "../data/"
OPTIMIZED_FILE = "../data/optimized_pairs.json"
RISK_CONFIG = "../data/risk_config.json"
FINAL_OUT = "../data/final_synergy.json"

PAYOUT_RATE = 100.0 
COST_PER_PAIR = 40.0  # ปรับเป็น 40 บาท (หน้า 10 + หลัง 10 ของเลข 2 ตัว ไม่ตัดซ้ำ)

def calculate_period_stats(draws, pair, days):
    """ฟังก์ชันคำนวณกำไรแบบละเอียด (รองรับเด้งเบิ้ล และ เด้งคู่จากรูดหน้า-หลังเต็มจำนวน)"""
    subset = draws[:days]
    if not subset: 
        return {"profit": 0, "win_rate": 0, "wins": 0, "invested": 0}
        
    wins, profit, invested = 0, 0, 0
    for row in subset:
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
            
        invested += COST_PER_PAIR
        
        # 🔻 ลอจิกตรวจสอบการถูกรางวัลแบบ "ไม่ตัดซ้ำ" 🔻
        hits = 0
        # ตรวจเลขตัวแรก (pair[0]) ในหลักสิบและหลักหน่วย
        if str(pair[0]) == num[0]: hits += 1  # ถูกรูดหน้า
        if str(pair[0]) == num[1]: hits += 1  # ถูกรูดหลัง
        
        # ตรวจเลขตัวที่สอง (pair[1]) ในหลักสิบและหลักหน่วย
        if str(pair[1]) == num[0]: hits += 1  # ถูกรูดหน้า
        if str(pair[1]) == num[1]: hits += 1  # ถูกรูดหลัง
        
        if hits > 0:
            wins += 1
            # คำนวณกำไรตามจำนวนเด้งที่ถูกจริง (1, 2 หรือมากกว่า)
            profit += (hits * PAYOUT_RATE) - COST_PER_PAIR
        else:
            profit -= COST_PER_PAIR
            
    return {
        "profit": profit,
        "win_rate": round((wins / len(subset)) * 100, 2),
        "wins": wins,
        "invested": invested
    }

def main():
    print("⏳ [Core Money] คำนวณแผนการลงทุน (กลยุทธ์รูดหน้า-หลัง 40 ชุด)...")
    
    if not os.path.exists(OPTIMIZED_FILE) or not os.path.exists(RISK_CONFIG):
        print("❌ ไม่พบไฟล์ข้อมูลจากขั้นตอนก่อนหน้า!")
        return
        
    with open(OPTIMIZED_FILE, 'r', encoding='utf-8') as f: opt_data = json.load(f).get("markets", {})
    with open(RISK_CONFIG, 'r', encoding='utf-8') as f: risk_data = json.load(f).get("markets", {})
    
    final_dashboard = {
        "portfolio": {
            "30d": {"profit": 0, "invested": 0, "wins": 0},
            "60d": {"profit": 0, "invested": 0, "wins": 0},
            "90d": {"profit": 0, "invested": 0, "wins": 0}
        },
        "markets": {}
    }

    for market_name, market_opt in opt_data.items():
        if not market_opt.get("pair"): continue
            
        pair = market_opt["pair"]
        min_wr = risk_data.get(market_name, {}).get("dynamic_min_winrate", 70.0)
        
        # 🔻 ประเมินความมั่นใจ (Confidence Score) 🔻
        conf = 100
        if market_opt["profit"] <= 0: conf -= 50
        if market_opt["win_rate"] < min_wr: conf -= ((min_wr - market_opt["win_rate"]) * 2)
        if market_opt.get("miss_latest", False): conf -= 40
        
        # 🛑 Sniper Filter
        if conf < 60 or market_opt["win_rate"] < (min_wr - 5):
            bet_size = 0
            status_color = "🔴 RED (NO TRADE)"
        else:
            bet_size = max(0, (int(conf) // 10) * 10)
            status_color = "🟢 GREEN" if bet_size >= 80 else "🟡 YELLOW"
        
        raw_file = os.path.join(DATA_DIR, f"raw_{market_name}.json")
        stats = {"30d": {}, "60d": {}, "90d": {}}
        
        if os.path.exists(raw_file):
            with open(raw_file, 'r', encoding='utf-8') as f: draws = json.load(f)
            stats["30d"] = calculate_period_stats(draws, pair, 30)
            stats["60d"] = calculate_period_stats(draws, pair, 60)
            stats["90d"] = calculate_period_stats(draws, pair, 90)
            
            # รวมยอดเข้า Portfolio (เฉพาะตัวที่มีโอกาสทำกำไร)
            for period in ["30d", "60d", "90d"]:
                final_dashboard["portfolio"][period]["profit"] += stats[period]["profit"]
                final_dashboard["portfolio"][period]["invested"] += stats[period]["invested"]
                final_dashboard["portfolio"][period]["wins"] += stats[period]["wins"]
        
        final_dashboard["markets"][market_name] = {
            "report": f"Sovereign V3 - {status_color}",
            "pair": pair,
            "bet_size": f"{bet_size}%",
            "market_threshold": f"{min_wr}%",
            "history": stats
        }
        
        print(f"🎯 {market_name.upper()} | คู่: {pair} | Bet: {bet_size}% | Status: {status_color} | Profit(30d): {stats['30d'].get('profit', 0)} ฿")

    with open(FINAL_OUT, 'w', encoding='utf-8') as f:
        json.dump(final_dashboard, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ [Core Money] อัปเดตพอร์ตรวม (กลยุทธ์ 40 ชุด) สำเร็จ!")

if __name__ == "__main__":
    main()
