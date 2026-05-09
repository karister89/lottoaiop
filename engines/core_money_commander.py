import json
import os

# =====================================================================
# ⚙️ Configuration - Core Money Commander (V3 Dashboard Edition)
# =====================================================================
DATA_DIR = "data"
OPTIMIZED_FILE = os.path.join(DATA_DIR, "optimized_pairs.json")
FINAL_OUT = os.path.join(DATA_DIR, "final_synergy.json")

PAYOUT_RATE = 100.0  
COST_PER_POS = 20.0 

def calculate_period_stats_split(draws, pair, position, days):
    """คำนวณสถิติกำไร-ขาดทุนย้อนหลังแยกช่วงเวลา 30/60/90 วัน"""
    subset = draws[:days]
    if not subset or not pair: 
        return {"profit": 0, "win_rate": 0, "wins": 0, "invested": 0}
        
    wins, profit, invested = 0, 0, 0
    p0, p1 = str(pair[0]), str(pair[1])
    
    for row in subset:
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
            
        invested += COST_PER_POS
        target = num[0] if position == 'front' else num[1]
        
        if p0 == target or p1 == target:
            wins += 1
            profit += (PAYOUT_RATE - COST_PER_POS)
        else:
            profit -= COST_PER_POS
            
    return {
        "profit": round(profit, 2),
        "win_rate": round((wins / len(subset)) * 100, 2) if len(subset) > 0 else 0,
        "wins": wins,
        "invested": invested
    }

def main():
    print("\n" + "="*75)
    print("💰 [Core Money V3] กำลังสร้างไฟล์สรุปบัญชี (30/60/90 วัน)...")
    print("="*75)
    
    # สร้างโฟลเดอร์ data หากไม่มี
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"📁 สร้างโฟลเดอร์ {DATA_DIR} เรียบร้อย")

    if not os.path.exists(OPTIMIZED_FILE):
        print(f"❌ Error: ไม่พบไฟล์ {OPTIMIZED_FILE} (กรุณารัน Optimizer ก่อน)")
        return
        
    with open(OPTIMIZED_FILE, 'r', encoding='utf-8') as f: 
        opt_data = json.load(f).get("markets", {})
    
    final_dashboard = {
        "portfolio": {
            "30d": {"profit": 0, "invested": 0, "wins": 0},
            "60d": {"profit": 0, "invested": 0, "wins": 0},
            "90d": {"profit": 0, "invested": 0, "wins": 0}
        },
        "markets": {}
    }

    phases = ["30d", "60d", "90d"]

    for market_name, data in opt_data.items():
        raw_file = os.path.join(DATA_DIR, f"raw_{market_name}.json")
        if not os.path.exists(raw_file): continue
            
        with open(raw_file, 'r', encoding='utf-8') as f: 
            draws = json.load(f)

        latest_date = draws[0].get('date', '') if draws else ""
        market_result = {"last_date": latest_date, "front": {}, "back": {}}

        # ประมวลผลฝั่งหน้า (Front)
        if data.get("front"):
            f_pair = data["front"]["pair"]
            f_bet = data["front"]["bet_size"]
            f_stats = { p: calculate_period_stats_split(draws, f_pair, 'front', int(p[:-1])) for p in phases }
            market_result["front"] = {"pair": f_pair, "bet_size": f_bet, "status": data["front"]["status"], "history": f_stats}
            if f_bet > 0:
                for p in phases:
                    final_dashboard["portfolio"][p]["profit"] += f_stats[p]["profit"]
                    final_dashboard["portfolio"][p]["invested"] += f_stats[p]["invested"]
                    final_dashboard["portfolio"][p]["wins"] += f_stats[p]["wins"]

        # ประมวลผลฝั่งหลัง (Back)
        if data.get("back"):
            b_pair = data["back"]["pair"]
            b_bet = data["back"]["bet_size"]
            b_stats = { p: calculate_period_stats_split(draws, b_pair, 'back', int(p[:-1])) for p in phases }
            market_result["back"] = {"pair": b_pair, "bet_size": b_bet, "status": data["back"]["status"], "history": b_stats}
            if b_bet > 0:
                for p in phases:
                    final_dashboard["portfolio"][p]["profit"] += b_stats[p]["profit"]
                    final_dashboard["portfolio"][p]["invested"] += b_stats[p]["invested"]
                    final_dashboard["portfolio"][p]["wins"] += b_stats[p]["wins"]

        final_dashboard["markets"][market_name] = market_result

    with open(FINAL_OUT, 'w', encoding='utf-8') as f:
        json.dump(final_dashboard, f, ensure_ascii=False, indent=4)
        
    print(f"✅ บันทึกไฟล์สำเร็จ -> {FINAL_OUT}")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
