import json
import os

# =====================================================================
# ⚙️ Configuration - Core Money Commander (V3 Split - 4 Phases Edition)
# =====================================================================
DATA_DIR = "data"
OPTIMIZED_FILE = os.path.join(DATA_DIR, "optimized_pairs.json")
FINAL_OUT = os.path.join(DATA_DIR, "final_synergy.json")

PAYOUT_RATE = 90.0  # เรทจ่าย (บาท)
COST_PER_POS = 20.0 # ทุนแยกฝั่งละ 20 บาท (รูดหน้า 2 เลข / รูดหลัง 2 เลข)

def calculate_period_stats_split(draws, pair, position, days):
    """ฟังก์ชันคำนวณกำไร-ขาดทุนย้อนหลังแยกสมรภูมิแบบระบุจำนวนวัน"""
    subset = draws[:days]
    if not subset or not pair: 
        return {"profit": 0, "win_rate": 0, "wins": 0, "invested": 0}
        
    wins, profit, invested = 0, 0, 0
    p0, p1 = str(pair[0]), str(pair[1])
    
    # วนลูปเช็คผลรางวัลย้อนหลังตามจำนวนวันที่กำหนด
    for row in subset:
        num = str(row.get('twoTop', '')).zfill(2)
        if not num.isdigit(): continue
            
        invested += COST_PER_POS
        # แยกเป้าหมายตามตำแหน่ง: หลักสิบ (num[0]) หรือ หลักหน่วย (num[1])
        target = num[0] if position == 'front' else num[1]
        
        # ตรวจสอบว่ารูด 2 เลขเข้าเป้าไหม
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
    print("💰 [Core Money V3] สรุปบัญชีแยกสมรภูมิ (15/30/60/100 วัน)...")
    print("="*75)
    
    if not os.path.exists(OPTIMIZED_FILE):
        print("❌ Error: ไม่พบไฟล์ optimized_pairs.json จากขั้นตอน Optimizer!")
        return
        
    with open(OPTIMIZED_FILE, 'r', encoding='utf-8') as f: 
        opt_data = json.load(f).get("markets", {})
    
    # เตรียมโครงสร้าง Dashboard (สรุปพอร์ตรวมตามแกนเวลาของพี่นพพล)
    final_dashboard = {
        "portfolio": {
            "15d": {"profit": 0, "invested": 0, "wins": 0},
            "30d": {"profit": 0, "invested": 0, "wins": 0},
            "60d": {"profit": 0, "invested": 0, "wins": 0},
            "100d": {"profit": 0, "invested": 0, "wins": 0}
        },
        "markets": {}
    }

    phases = ["15d", "30d", "60d", "100d"]

    for market_name, data in opt_data.items():
        raw_file = os.path.join(DATA_DIR, f"raw_{market_name}.json")
        if not os.path.exists(raw_file): continue
            
        with open(raw_file, 'r', encoding='utf-8') as f: 
            draws = json.load(f)

        market_result = {"front": {}, "back": {}}

        # 🎯 สมรภูมิฝั่งหน้า (Front / หลักสิบ)
        if data.get("front"):
            f_pair = data["front"]["pair"]
            f_bet = data["front"]["bet_size"]
            f_stats = { p: calculate_period_stats_split(draws, f_pair, 'front', int(p[:-1])) for p in phases }
            
            market_result["front"] = {
                "pair": f_pair,
                "bet_size": f_bet,
                "status": data["front"]["status"],
                "history": f_stats
            }
            # รวมเข้า Portfolio (เฉพาะฝั่งที่บอทสั่งลุย Bet > 0)
            if f_bet > 0:
                for p in phases:
                    final_dashboard["portfolio"][p]["profit"] += f_stats[p]["profit"]
                    final_dashboard["portfolio"][p]["invested"] += f_stats[p]["invested"]
                    final_dashboard["portfolio"][p]["wins"] += f_stats[p]["wins"]

        # 🎯 สมรภูมิฝั่งหลัง (Back / หลักหน่วย)
        if data.get("back"):
            b_pair = data["back"]["pair"]
            b_bet = data["back"]["bet_size"]
            b_stats = { p: calculate_period_stats_split(draws, b_pair, 'back', int(p[:-1])) for p in phases }
            
            market_result["back"] = {
                "pair": b_pair,
                "bet_size": b_bet,
                "status": data["back"]["status"],
                "history": b_stats
            }
            # รวมเข้า Portfolio (เฉพาะฝั่งที่บอทสั่งลุย Bet > 0)
            if b_bet > 0:
                for p in phases:
                    final_dashboard["portfolio"][p]["profit"] += b_stats[p]["profit"]
                    final_dashboard["portfolio"][p]["invested"] += b_stats[p]["invested"]
                    final_dashboard["portfolio"][p]["wins"] += b_stats[p]["wins"]

        final_dashboard["markets"][market_name] = market_result
        
        # ปริ้นท์สรุปสั้นๆ ใน Console ให้พี่ดู
        f_p = market_result.get('front', {}).get('history', {}).get('15d', {}).get('profit', 0)
        b_p = market_result.get('back', {}).get('history', {}).get('15d', {}).get('profit', 0)
        print(f"📊 {market_name.upper():<12} | กำไร(15วัน) -> หน้า: {f_p:+.0f} ฿ | หลัง: {b_p:+.0f} ฿")

    # บันทึกข้อมูลสุทธิ เพื่อรอการแสดงผลบน index.html
    with open(FINAL_OUT, 'w', encoding='utf-8') as f:
        json.dump(final_dashboard, f, ensure_ascii=False, indent=4)
        
    print("\n" + "="*75)
    print(f"✅ [Core Money] สรุปบัญชีสำเร็จ! (15/30/60/100 วัน)")
    print(f"📈 พอร์ตรวม 15 วันล่าสุด: {final_dashboard['portfolio']['15d']['profit']:+.0f} ฿")
    print("="*75 + "\n")

if __name__ == "__main__":
    main()
