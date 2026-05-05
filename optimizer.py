import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math

# ==========================================
# ⚙️ CONFIGURATION (ULTIMATE OPTIMIZER)
# ==========================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
MARKETS = {
    'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG',
    'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX',
    'uk': 'FTSE', 'dow': 'DJI'
}

STATIC_VETO = {
    'nikkei': 1.15, 'china': 1.15, 'hangseng': 1.20,
    'taiwan': 1.15, 'india': 1.15, 'germany': 1.15,
    'uk': 1.25, 'dow': 1.35
}

BET_CONFIG = { "COST_PER_DIGIT": 19, "PAYOUT": 100 }
TEST_DAYS = 30 

# สแกนปูพรมแบบกว้างมากๆ
LIMIT_RANGE = range(40, 101, 1)  
ELITE_RANGE = range(10, 61, 1)   

# ==========================================
# 🧠 ALGORITHMS
# ==========================================
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

def build_bots():
    bots = []; windows = [10, 18, 28, 50, 80, 130, 190, 250, 350, 500]; bot_id = 1
    for w in windows:
        for algo in ALGO_MAP.keys():
            bots.append({'id': f"B{bot_id:03d}", 'type': algo, 'window': w, 'name': f"{algo.upper()}-{w}"})
            bot_id += 1
    return bots
BOTS = build_bots()

def get_top3_digit(scores):
    ranked = sorted([{'digit': str(i), 'score': scores[i]} for i in range(10)], key=lambda x: x['score'], reverse=True)
    return ranked[:3]

def main():
    print("🔥 เริ่มต้นสแกนหาค่า God Parameters (Focus: MAX Win-Rate & Force SKIP)...")
    
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json:
        print("❌ ERROR: ไม่พบตัวแปร GCP_CREDENTIALS")
        exit(1)

    creds_dict = json.loads(creds_json)
    client = gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    sheet = client.open_by_key(SHEET_ID)

    best_settings = {}

    for key, sheet_name in MARKETS.items():
        try:
            print(f"\n🎯 สแกนปูพรมตลาด: {key.upper()} (หมุนหา 3,000+ รูปแบบ...)")
            
            ws = sheet.worksheet(sheet_name)
            rows = ws.get_all_values()[2:]
            parsed_draws = []
            for r in rows:
                if not r or not r[0].strip(): continue
                r += [""] * (9 - len(r))
                ds = r[0].strip()
                try:
                    p = ds.split('/')
                    if len(p) == 3: ds = f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}"
                except: pass
                parsed_draws.append({
                    "date": ds, "twoTop": str(r[3]).strip().zfill(2) if r[3].strip() else "",
                    "diffOpen": float(r[4]) if r[4].strip() else 0, "diff": float(r[5]) if r[5].strip() else 0, "open": float(r[6]) if r[6].strip() else 0, "table": float(r[7]) if r[7].strip() else 0
                })
            
            draws = sorted(list({d['date']: d for d in parsed_draws}.values()), key=lambda x: x['date'], reverse=True)
            if len(draws) < 30: continue

            max_idx = min(len(draws), TEST_DAYS + 90 + 15)
            matrix = {b['id']: {'twoTop': {}} for b in BOTS}
            for b in BOTS:
                algo_func = ALGO_MAP[b['type']]
                for i in range(max_idx):
                    subset = draws[i : i + b['window']]
                    if not subset: continue
                    matrix[b['id']]['twoTop'][i] = get_top3_digit(algo_func(subset, 'twoTop'))

            results = []
            target_veto = STATIC_VETO.get(key, 1.20)

            for min_elite in ELITE_RANGE:
                for base_limit in LIMIT_RANGE:
                    pT, wT, sT, mis = 0, 0, 0, 0
                    for day_idx in range(1, TEST_DAYS + 1):
                        limit_days = min(len(draws) - day_idx - 15, 90)
                        hits = {b['id']: 0 for b in BOTS}
                        for i in range(1, limit_days + 1):
                            test_idx = day_idx + i
                            actual = draws[test_idx-1]
                            for b in BOTS:
                                pTop = matrix[b['id']]['twoTop'].get(test_idx)
                                if pTop and pTop[0]['digit'] in actual['twoTop']: hits[b['id']] += 1
                        
                        evals = []
                        for b in BOTS:
                            wr = (hits[b['id']] / limit_days) * 100 if limit_days > 0 else 0
                            pwr = 3.0 if wr >= min_elite else (1.0 if wr >= 21 else (0.5 if wr >= 16 else 0))
                            evals.append({**b, 'winRate': wr, 'power': pwr, 'isShadow': pwr == 0})
                        
                        vote = [0.0]*10
                        for eb in evals:
                            if eb['isShadow']: continue
                            preds = matrix[eb['id']]['twoTop'].get(day_idx, [])
                            for i, r in enumerate(preds): vote[int(r['digit'])] += eb['power'] * (1 - i * 0.2)
                        
                        ranked = sorted([(str(i), vote[i]) for i in range(10)], key=lambda x: x[1], reverse=True)
                        top, sec, fourth = ranked[0][1], ranked[1][1], (ranked[3][1] if len(ranked)>3 else 0)
                        chaos = (fourth / top * 100) if top > 0 else 100
                        
                        is_veto = (chaos > base_limit and top > sec * target_veto)
                        sig_raw = 'RED' if chaos > base_limit else ('YELLOW' if chaos > (base_limit-15) else 'GREEN')
                        final_sig = 'YELLOW' if (sig_raw == 'RED' and is_veto) else sig_raw
                        
                        is_win = ranked[0][0] in draws[day_idx-1]['twoTop']
                        
                        if final_sig != 'RED':
                            pT += 1
                            if is_win: wT += 1
                        else:
                            sT += 1
                            if is_win: mis += 1 
                    
                    cost, rev = pT * BET_CONFIG["COST_PER_DIGIT"], wT * BET_CONFIG["PAYOUT"]
                    profit = rev - cost
                    winrate = (wT / pT * 100) if pT > 0 else 0
                    
                    if pT < 4 or profit <= 0:
                        continue 
                        
                    score = (winrate * 1000) + profit - (mis * 10) 
                    
                    results.append({
                        'base_limit': base_limit, 'min_elite': min_elite, 'profit': profit, 
                        'wr': winrate, 'played': pT, 'skipped': sT, 'missed': mis, 'score': score
                    })

            # 🛑 ระบบ FORCE AUTO-SKIP (บังคับปิดตลาด ไม่เล่นเลย 100%)
            if len(results) == 0:
                print(f"⚠️ ตลาด {key.upper()} สวิงหนัก! หาจังหวะทำกำไรไม่ได้เลย")
                print("🛑 สับสวิตช์สั่ง AUTO-SKIP (Limit: -1) เพื่อบังคับให้หวยออกไฟแดง ป้องกันเงินทุน!")
                top_config = {
                    'base_limit': -1,    # ทำให้ Chaos > Limit เป็นจริงเสมอ (บังคับไฟแดงทุกงวด)
                    'min_elite': 100,    # ตั้ง Elite ไว้สูงๆ เพื่อลดบทบาทบอท
                    'wr': 0, 
                    'profit': 0, 
                    'played': 0, 
                    'missed': 0
                }
            else:
                results.sort(key=lambda x: x['score'], reverse=True)
                top_config = results[0] 
            
            best_settings[key] = {
                'base_limit': top_config['base_limit'],
                'min_elite': top_config['min_elite'],
                'veto_mult': target_veto
            }
            
            if top_config['base_limit'] == -1:
                print(f"✅ บังคับปิดระบบการเล่น (SKIP ตลอดวัน) สำหรับ {key.upper()}")
            else:
                print(f"✅ ตั้งค่าล่าสุด: Limit = {top_config['base_limit']}, Elite = {top_config['min_elite']}")
                print(f"   📊 [Win Rate: {top_config['wr']:.1f}%] [กำไร: {top_config['profit']}฿] [เล่น: {top_config['played']}] [พลาดไฟแดง: {top_config['missed']}]")

        except Exception as e:
            print(f"❌ Error ตลาด {sheet_name}: {e}")

    with open('market_settings.json', 'w', encoding='utf-8') as f:
        json.dump(best_settings, f, ensure_ascii=False, indent=2)
    print("\n🎉 บันทึกค่าความโหดลง market_settings.json เรียบร้อย!")

if __name__ == "__main__": main()
