import json
import os

# =====================================================================
# ⚙️ Configuration - Core Money Commander
# =====================================================================
DATA_DIR = "../data/"
OPTIMIZED_FILE = "../data/optimized_pairs.json"
RISK_CONFIG = "../data/risk_config.json"
FINAL_OUT = "../data/final_synergy.json"

PAYOUT_RATE = 100.0
COST_PER_PAIR = 38.0

def calculate_period_stats(draws, pair, days):
    """ฟังก์ชันไทม์แมชชีนย้อนหลังคำนวณกำไร/ขาดทุนตามจำนวนวันที่กำหนด"""
    subset = draws[:days]
    if not subset: 
        return {"profit": 0, "win_rate": 0, "wins": 0, "invested": 0}
        
    wins, profit, invested = 0, 0, 0
    for row in subset:
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
            
        invested += COST_PER_PAIR
        # รูดหน้า/หลังเข้า นับเด้ง
        hits = (1 if str(pair[0]) in num else 0) + (1 if str(pair[1]) in num else 0)
        if hits > 0:
            wins += 1
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
    print("⏳ [Core Money] คำนวณแผนการลงทุนและสรุปพอร์ตรวม 30/60/90 วัน...")
    
    # โหลดคู่เลขเด็ดและมาตรฐานความเสี่ยง
    if not os.path.exists(OPTIMIZED_FILE) or not os.path.exists(RISK_CONFIG):
        print("❌ ขาดไฟล์ข้อมูลจากกุนซือคนก่อนหน้า!")
        return
        
    with open(OPTIMIZED_FILE, 'r', encoding='utf-8') as f: opt_data = json.load(f).get("markets", {})
    with open(RISK_CONFIG, 'r', encoding='utf-8') as f: risk_data = json.load(f).get("markets", {})
    
    # โครงสร้างสำหรับส่งขึ้นหน้าเว็บ (index.html)
    final_dashboard = {
        "portfolio": {
            "30d": {"profit": 0, "invested": 0, "wins": 0},
            "60d": {"profit": 0, "invested": 0, "wins": 0},
            "90d": {"profit": 0, "invested": 0, "wins": 0}
        },
        "markets": {}
    }

    # วนลูปเช็คบิลทีละตลาด
    for market_name, market_opt in opt_data.items():
        if not market_opt.get("pair"): continue
            
        pair = market_opt["pair"]
        min_wr = risk_data.get(market_name, {}).get("dynamic_min_winrate", 70.0)
        
        # 🔻 ลอจิกกฎเหล็กดั้งเดิมของพี่นพพล 🔻
        conf = 100
        if market_opt["profit"] <= 0: 
            conf -= 50
        if market_opt["win_rate"] < min_wr: 
            conf -= ((min_wr - market_opt["win_rate"]) * 2)
        if market_opt.get("miss_latest", False): 
            conf -= 40
        
        bet_size = max(0, (int(conf) // 10) * 10)
        status_color = "🟢 GREEN" if bet_size >= 80 else "🟡 YELLOW" if bet_size >= 40 else "🔴 RED"
        
        # โหลดข้อมูลดิบของตลาดนี้เพื่อทำสถิติ 30/60/90 วัน
        raw_file = os.path.join(DATA_DIR, f"raw_{market_name}.json")
        stats = {"30d": {}, "60d": {}, "90d": {}}
        
        if os.path.exists(raw_file):
            with open(raw_file, 'r', encoding='utf-8') as f: draws = json.load(f)
            stats["30d"] = calculate_period_stats(draws, pair, 30)
            stats["60d"] = calculate_period_stats(draws, pair, 60)
            stats["90d"] = calculate_period_stats(draws, pair, 90)
            
            # บวกยอดเข้า "พอร์ตกองทุนรวม (Portfolio)"
            for period in ["30d", "60d", "90d"]:
                final_dashboard["portfolio"][period]["profit"] += stats[period]["profit"]
                final_dashboard["portfolio"][period]["invested"] += stats[period]["invested"]
                final_dashboard["portfolio"][period]["wins"] += stats[period]["wins"]
        
        # จัดแพ็กเกจของตลาดนี้
        final_dashboard["markets"][market_name] = {
            "report": f"Sovereign V3 - {status_color}",
            "pair": pair,
            "bet_size": f"{bet_size}%",
            "market_threshold": f"{min_wr}%",
            "history": stats
        }
        
        print(f"🎯 {market_name.upper()} | คู่: {pair} | ลงเงิน: {bet_size}% | สถานะ: {status_color} | กำไร 30 วัน: {stats['30d'].get('profit', 0)} ฿")

    # บันทึกเป็นไฟล์เดียว ส่งขึ้นหน้าเว็บ!
    with open(FINAL_OUT, 'w', encoding='utf-8') as f:
        json.dump(final_dashboard, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ [Core Money] สรุปยอด Portfolio สำเร็จ! (เตรียมส่งข้อมูลเข้า Dashboard)")

if __name__ == "__main__":
    main()
