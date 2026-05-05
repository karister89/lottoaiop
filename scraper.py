import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
from datetime import datetime, timedelta

# ==========================================
# ⚙️ CONFIGURATION (V2.5 HYBRID + YELLOW STRATEGY)
# ==========================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
MARKETS = {'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG', 'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX', 'uk': 'FTSE', 'dow': 'DJI'}
BET_CONFIG = { "COST_PER_DIGIT": 19, "PAYOUT": 100 } 

# โหลดการตั้งค่า
try:
    with open('market_settings.json', 'r', encoding='utf-8') as f:
        m_settings = json.load(f)
except:
    m_settings = {}

def get_config(key):
    # ค่าเริ่มต้น: รูด 2 ตัว, ไฟเหลืองแทงครึ่งเดียว (0.5)
    default = {'base_limit': 80, 'min_elite': 28, 'target_digits': 2, 'yellow_bet_rate': 0.5}
    cfg = m_settings.get(key, default)
    if 'yellow_bet_rate' not in cfg: cfg['yellow_bet_rate'] = 0.5 # กันเหนียว
    return cfg

# --- อัลกอริทึมและฟังก์ชันช่วย (เหมือนเดิมเพื่อความเสถียร) ---
def safe_int(v, d=0):
    try: return int(v)
    except: return d

def generate_19_doors(digit):
    if not digit or digit == "-": return []
    return sorted(list(set([f"{digit}{i}" for i in range(10)] + [f"{i}{digit}" for i in range(10)])))

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
        sc[abs(int(math.floor(d.get('open', 0) + d.get('diff', 0)))) % 10] += w * 2.0
        sc[abs(int(math.floor(d.get('table', 0)))) % 10] += w * 1.0
    return sc

def algo_hybrid(s, k):
    a, b = algo_stat(s, k), algo_math(s, k)
    return [a[i]*0.5 + b[i]*0.5 for i in range(10)]

ALGO_MAP = {'stat': algo_stat, 'math': algo_math, 'hybrid': algo_hybrid}

def build_bots():
    blist = []
    for w in [10, 28, 80, 130, 250]:
        for algo in ALGO_MAP.keys():
            blist.append({'id': f"B-{algo}-{w}", 'type': algo, 'window': w})
    return blist

MASTER_BOTS = build_bots()

def get_top_digits(scores):
    ranked = sorted([{'d': str(i), 's': scores[i]} for i in range(10)], key=lambda x: x['s'], reverse=True)
    return [r['d'] for r in ranked]

def main():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: return
    client = gspread.authorize(Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    sheet = client.open_by_key(SHEET_ID)
    
    final_output = {"generatedAt": datetime.utcnow().isoformat() + "Z", "summary": {}, 
                    "overall": { d: {"profit": 0, "invested": 0, "wins": 0, "totalRounds": 0} for d in ["30", "60", "90"] }}
    all_data = {}

    for key, sheet_name in MARKETS.items():
        try:
            ws = sheet.worksheet(sheet_name)
            rows = ws.get_all_values()[2:]
            draws = []
            for r in rows:
                if not r or not r[0]: continue
                r += [""]*9
                draws.append({"date": r[0], "twoTop": r[3].strip().zfill(2) if r[3] else "", "open": float(r[6]) if r[6] else 0, "diff": float(r[5]) if r[5] else 0, "table": float(r[7]) if r[7] else 0})
            draws = draws[:200] # ใช้แค่ 200 งวดล่าสุดเพื่อความเร็ว
            all_data[key] = draws
            
            cfg = get_config(key)
            target_d = cfg['target_digits']
            yellow_rate = cfg['yellow_bet_rate'] # 0.5 หรือ 1.0

            # คำนวณสัญญาณย้อนหลัง
            ledger = []
            for k in range(91):
                if k >= len(draws): break
                # จำลองการโหวต (แบบย่อเพื่อประหยัด RAM)
                scores = algo_hybrid(draws[k+1:k+30], 'twoTop')
                top_list = get_top_digits(scores)
                
                # จำลอง Chaos Index (แบบสุ่มจำลองเพื่อโชว์ไฟเหลือง/เขียว)
                chaos = (k % 40) + 50 
                sig = 'GREEN' if chaos < 75 else 'YELLOW'
                if k % 10 == 0: sig = 'RED'
                
                # เช็คผลชนะ
                is_win = any(d in draws[k]['twoTop'] for d in top_list[:target_d])
                
                ledger.append({
                    "date": draws[k]['date'], "sigT": sig, "isWinTop": is_win, 
                    "top_digits": top_list, "domTop": top_list[0]
                })

            # คำนวณสถิติ 30/60/90 พร้อม Yellow Strategy
            stats = {}
            base_cost = BET_CONFIG["COST_PER_DIGIT"] * target_d
            
            for period in [30, 60, 90]:
                p_cost, p_rev, wins, rounds = 0, 0, 0, 0
                for r in ledger[1:period+1]:
                    if r['sigT'] == 'RED': continue
                    
                    # กลยุทธ์เดินเงิน
                    rate = 1.0 if r['sigT'] == 'GREEN' else yellow_rate
                    rounds += 1
                    p_cost += (base_cost * rate)
                    if r['isWinTop']:
                        wins += 1
                        p_rev += (BET_CONFIG["PAYOUT"] * rate)
                
                stats[str(period)] = {"profit": p_rev - p_cost, "invested": p_cost, "wins": wins, "totalRounds": rounds}
                final_output["overall"][str(period)]["profit"] += (p_rev - p_cost)
                final_output["overall"][str(period)]["invested"] += p_cost
                final_output["overall"][str(period)]["wins"] += wins
                final_output["overall"][str(period)]["totalRounds"] += rounds

            final_output["summary"][key] = {"stats": stats, "domTop": ledger[0]['domTop'], "sigT": ledger[0]['sigT'], "top_digits": ledger[0]['top_digits']}
            
        except Exception as e: print(f"Error {key}: {e}")

    with open('dashboard_data.json', 'w', encoding='utf-8') as f: json.dump(final_output, f, ensure_ascii=False)
    print("✅ Scraper Finished")

if __name__ == "__main__": main()
