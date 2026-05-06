import json
import os
import math

# ======================================================================
# ⚙️ แผงควบคุมหลัก (CONTROL PANEL) - เปลี่ยนแปลงค่าต่างๆ ได้ที่นี่ที่เดียว!
# ======================================================================

# --- 1. ตั้งค่าการแทง (Betting Rules) ---
TARGET_DIGITS = 2               # จำนวนตัวเลขที่จะรูด (ค่าปกติ 2)
HARDCORE_SPLIT_MODE = True      # เปิดระบบแยกไม้แทง (True = เปิด, False = ปิด)
YELLOW_BET_RATE = 0.5           # สัดส่วนเงินตอนติดไฟเหลือง (0.5 คือแทงครึ่งราคาสำหรับเบอร์ 2)
VETO_MULT = 9.99                # ปิดระบบ Veto (ตั้ง 9.99 คือปิดถาวร เพื่อให้กราฟนิ่ง)

# --- 2. ตั้งค่าความละเอียดการค้นหา (Grid Search Tuning) ---
# ค้นหาจุดตัดไฟแดง (Base Limit)
LIMIT_START = 60                # เริ่มต้นหาที่ค่า (แนะนำ 70)
LIMIT_END = 90                  # สิ้นสุดหาที่ค่า (แนะนำ 90)
LIMIT_STEP = 1                  # ขยับทีละ (แนะนำ 5)

# ค้นหา Win-Rate ของบอทหัวกะทิ (Elite Win-Rate %)
ELITE_START = 30                # เริ่มต้นหาที่ค่า Win-Rate (แนะนำ 15)
ELITE_END = 80                  # สิ้นสุดหาที่ค่า Win-Rate (แนะนำ 45)
ELITE_STEP = 1                  # ขยับทีละ (แนะนำ 2)

# --- 3. ตั้งค่าระบบไฟล์ (System Variables) ---
BACKTEST_DAYS = 90
DATA_FILE = 'lottery-data.json'
OUTPUT_SETTINGS = 'market_settings.json'
PAYOUT = 100
COST_UNIT = 19 * TARGET_DIGITS

# ======================================================================
# 🤖 สิ้นสุดเขตแผงควบคุม (ส่วนด้านล่างคือระบบประมวลผล ไม่ต้องแก้ไข)
# ======================================================================

def safe_int(val, default=0):
    try: return int(val)
    except: return default

def algo_stat(s, k):
    sc = [0.0]*10
    for i, d in enumerate(s):
        v = d.get(k, "")
        if len(v) == 2:
            w = math.exp(-i/15.0) * 1.5 
            sc[safe_int(v[0])] += w; sc[safe_int(v[1])] += w
    return sc

def algo_math(s, k):
    sc = [0.0]*10
    for i, d in enumerate(s):
        w = 3.0 if i < 5 else (1.5 if i < 15 else 0.5) 
        o, diff, table = d.get('open', 0), d.get('diff', 0), d.get('table', 0)
        sc[abs(int(math.floor(o + diff))) % 10] += w * 2.0 
        sc[abs(int(math.floor(table))) % 10] += w * 1.0 
    return sc

def algo_cipher(s, k):
    sc = [0.0]*10
    for i in range(min(len(s), 15)):
        w = math.exp(-i/8.0) * 3 
        diff = s[i].get('diff', 0)
        sc[abs(int(math.floor(diff * 7))) % 10] += w * 2.0 
        sc[abs(int(math.floor(diff * 13))) % 10] += w * 1.5 
    return sc

def algo_science(s, k):
    sc = [0.0]*10
    for i in range(min(len(s), 30)):
        v = s[i].get(k, "")
        if len(v) == 2:
            w = 2.5 if i < 8 else 1.0 
            sc[abs(safe_int(v[0]) - safe_int(v[1]))] += w * 1.5
            sc[(safe_int(v[0]) + safe_int(v[1])) % 10] += w * 1.5
    return sc

def algo_hybrid(s, k):
    a = algo_stat(s, k); b = algo_math(s, k); c = algo_cipher(s, k)
    return [a[i]*0.35 + b[i]*0.35 + c[i]*0.30 for i in range(10)] 

ALGO_MAP = {'stat': algo_stat, 'math': algo_math, 'science': algo_science, 'cipher': algo_cipher, 'hybrid': algo_hybrid}

def get_bots_master():
    blist = []
    windows = [10, 18, 28, 50, 80, 130, 190, 250, 350, 500]
    bot_id = 1
    for w in windows:
        for algo in ALGO_MAP.keys():
            blist.append({'id': f"B{bot_id:03d}", 'type': algo, 'window': w})
            bot_id += 1
    return blist

def main():
    if not os.path.exists(DATA_FILE): 
        print(f"❌ Error: ไม่พบไฟล์ข้อมูล {DATA_FILE} กรุณารัน Scraper ก่อน")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f: 
        master_data = json.load(f)

    lotteries = master_data.get('lotteries', {})
    optimized_settings = {}
    BOTS_LIST = get_bots_master()

    for key, draws in lotteries.items():
        if len(draws) < 50: continue
        print(f"🔎 ค้นหาค่า Best Parameters สำหรับ: {key} (กำลังสแกนแบบละเอียด...)")

        matrix = {b['id']: {} for b in BOTS_LIST}
        for b in BOTS_LIST:
            func = ALGO_MAP[b['type']]
            for i in range(BACKTEST_DAYS + 30):
                subset = draws[i : i + b['window']]
                if not subset: continue
                scores = func(subset, 'twoTop')
                ranked = sorted([{'d': str(x), 's': scores[x]} for x in range(10)], key=lambda x: x['s'], reverse=True)
                matrix[b['id']][i] = [r['d'] for r in ranked[:5]]

        best_profit = -999999
        best_cfg = {'base_limit': 80, 'min_elite': 28, 'veto_mult': VETO_MULT, 'target_digits': TARGET_DIGITS, 'yellow_bet_rate': YELLOW_BET_RATE, 'hardcore_mode': HARDCORE_SPLIT_MODE}

        # ==========================================
        # 🎯 ระบบ Grid Search (ใช้ค่าจากแผงควบคุมด้านบน)
        # ==========================================
        for base in range(LIMIT_START, LIMIT_END + 1, LIMIT_STEP):
            for elite in range(ELITE_START, ELITE_END + 1, ELITE_STEP):
                sim_profit = 0
                for k in range(1, BACKTEST_DAYS + 1):
                    if k >= len(draws): break
                    evals = []
                    lookback = min(len(draws) - k - 5, 60)
                    for b in BOTS_LIST:
                        hits = 0
                        for i in range(1, lookback + 1):
                            idx = k + i
                            if idx >= len(draws): continue
                            if matrix[b['id']].get(idx) and matrix[b['id']][idx][0] in draws[idx-1]['twoTop']: hits += 1
                        wr = (hits/lookback*100) if lookback > 0 else 0
                        if wr >= elite: evals.append({'id': b['id'], 'pwr': 3.0})
                        elif wr >= 21: evals.append({'id': b['id'], 'pwr': 1.0})

                    if not evals: continue

                    vote = [0.0]*10
                    for eb in evals:
                        preds = matrix[eb['id']].get(k, [])
                        for i, dgt in enumerate(preds[:3]): vote[int(dgt)] += eb['pwr'] * (1 - i * 0.2)
                    
                    ranked_v = sorted([(str(x), v) for x, v in enumerate(vote)], key=lambda x: x[1], reverse=True)
                    top, sec, fourth = ranked_v[0][1], ranked_v[1][1], (ranked_v[3][1] if len(ranked_v)>3 else 0)
                    chaos = (fourth / top * 100) if top > 0 else 100
                    
                    is_veto = (chaos > base and top > sec * VETO_MULT)
                    sig = 'RED' if chaos > base else 'GREEN'
                    if sig == 'RED' and is_veto: sig = 'YELLOW'

                    if sig != 'RED':
                        played = [r[0] for r in ranked_v[:TARGET_DIGITS]]
                        # --------------------------------------------
                        # สูตรคำนวณแยกไม้แทง (Hardcore Mode)
                        # --------------------------------------------
                        if HARDCORE_SPLIT_MODE and sig == 'YELLOW' and TARGET_DIGITS >= 2:
                            cost = (19 * 1.0) + (19 * YELLOW_BET_RATE)
                            win_amount = 0
                            if played[0] in draws[k]['twoTop']: win_amount += PAYOUT * 1.0
                            elif played[1] in draws[k]['twoTop']: win_amount += PAYOUT * YELLOW_BET_RATE
                            sim_profit += win_amount - cost
                        else:
                            current_rate = 1.0 if sig == 'GREEN' else YELLOW_BET_RATE
                            if any(d in draws[k]['twoTop'] for d in played):
                                sim_profit += (PAYOUT * current_rate) - (COST_UNIT * current_rate)
                            else: sim_profit -= (COST_UNIT * current_rate)
                
                if sim_profit > best_profit:
                    best_profit = sim_profit
                    best_cfg = {'base_limit': base, 'min_elite': elite, 'veto_mult': VETO_MULT, 'target_digits': TARGET_DIGITS, 'yellow_bet_rate': YELLOW_BET_RATE, 'hardcore_mode': HARDCORE_SPLIT_MODE}

        optimized_settings[key] = best_cfg
        print(f"✅ {key} -> Limit: {best_cfg['base_limit']}, Elite: {best_cfg['min_elite']} (คาดการณ์กำไรย้อนหลัง: {best_profit})")

    with open(OUTPUT_SETTINGS, 'w', encoding='utf-8') as f: 
        json.dump(optimized_settings, f, ensure_ascii=False, indent=2)
    print(f"🚀 บันทึกการตั้งค่าลง {OUTPUT_SETTINGS} เรียบร้อย!")

if __name__ == "__main__": 
    main()
