import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
from datetime import datetime, timedelta

# ======================================================================
# ⚙️ แผงควบคุมหลัก (CONTROL PANEL)
# ======================================================================

# --- 1. ตั้งค่าการเงิน (Financial Settings) ---
COST_PER_DIGIT = 19             
PAYOUT = 100                    

# --- 2. ค่าเริ่มต้นกรณีหาไฟล์ Config ไม่เจอ (Fallback Defaults) ---
DEFAULT_BASE_LIMIT = 80         
DEFAULT_MIN_ELITE = 28          
DEFAULT_TARGET_DIGITS = 2       
DEFAULT_YELLOW_RATE = 0.5       
DEFAULT_HC_MODE = False         

# --- 3. ข้อมูลทางเทคนิค (System Config) ---
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
RAW_DATA_FILE = 'data_raw.json'          # ไฟล์ข้อมูลดิบสำหรับ Optimizer
DASHBOARD_FILE = 'data_dashboard.json'  # ไฟล์สรุปผลสำหรับหน้าเว็บ
SETTINGS_FILE = 'config_markets.json'    # ไฟล์ตั้งค่าที่ได้จาก Optimizer

MARKETS = {
    'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG', 
    'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX', 
    'uk': 'FTSE', 'dow': 'DJI'
}

# ======================================================================
# 🤖 ระบบประมวลผล (Internal Logic)
# ======================================================================

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def get_config(settings, key):
    return settings.get(key, {
        'base_limit': DEFAULT_BASE_LIMIT, 
        'min_elite': DEFAULT_MIN_ELITE, 
        'target_digits': DEFAULT_TARGET_DIGITS, 
        'yellow_bet_rate': DEFAULT_YELLOW_RATE, 
        'hardcore_mode': DEFAULT_HC_MODE
    })

def safe_int(v, d=0):
    try: return int(v)
    except: return d

def generate_19_doors(digit):
    if not digit or digit == "-": return []
    return sorted(list(set([f"{digit}{i}" for i in range(10)] + [f"{i}{digit}" for i in range(10)])))

def algo_hybrid(s, k):
    sc = [0.0]*10
    for i, d in enumerate(s):
        v = d.get(k, "")
        if len(v) == 2:
            w = math.exp(-i/15.0) * 2.0
            sc[safe_int(v[0])] += w; sc[safe_int(v[1])] += w
    return sc

def get_top_digits(scores):
    ranked = sorted([{'d': str(i), 's': scores[i]} for i in range(10)], key=lambda x: x['s'], reverse=True)
    return [r['d'] for r in ranked]

def main():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: return
    client = gspread.authorize(Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    sheet = client.open_by_key(SHEET_ID)
    
    settings = load_settings()
    final_output = {"generatedAt": datetime.utcnow().isoformat() + "Z", "summary": {}, "overall": { d: {"profit": 0, "invested": 0, "wins": 0, "totalRounds": 0} for d in ["30", "60", "90"] }}
    master_lottery_store = {}

    for key, sheet_name in MARKETS.items():
        try:
            ws = sheet.worksheet(sheet_name)
            rows = ws.get_all_values()[2:]
            draws = []
            for r in rows:
                if not r or not r[0]: continue
                r += [""]*9
                draws.append({
                    "date": r[0], "twoTop": r[3].strip().zfill(2) if r[3] else "",
                    "open": float(r[1]) if r[1] else 0, "diff": float(r[2]) if r[2] else 0,
                    "table": float(r[4]) if len(r) > 4 and r[4] else 0
                })
            
            master_lottery_store[key] = draws
            cfg = get_config(settings, key)
            target_d = cfg.get('target_digits', DEFAULT_TARGET_DIGITS)
            y_rate = cfg.get('yellow_bet_rate', DEFAULT_YELLOW_RATE)
            is_hc = cfg.get('hardcore_mode', DEFAULT_HC_MODE)
            
            ledger = []
            for k in range(min(len(draws)-1, 92)):
                scores = algo_hybrid(draws[k+1:k+31], 'twoTop')
                top_list = get_top_digits(scores)
                chaos = (k % 35) + 45 
                sig = 'GREEN' if chaos < 70 else 'YELLOW'
                if k % 12 == 0: sig = 'RED'
                played = top_list[:target_d]
                win_idx = next((i for i, d in enumerate(played) if d in draws[k]['twoTop']), -1)
                ledger.append({"date": draws[k]['date'], "sigT": sig, "isWinTop": (win_idx != -1), "winIndex": win_idx, "top_digits": top_list, "domTop": top_list[0]})

            stats_p = {}
            for period in [30, 60, 90]:
                p_net, p_inv, p_wins, p_rounds = 0, 0, 0, 0
                for r in ledger[1:period+1]:
                    if r['sigT'] == 'RED': continue
                    p_rounds += 1
                    cost = (COST_PER_DIGIT * 1.0) + (COST_PER_DIGIT * y_rate) if is_hc and r['sigT'] == 'YELLOW' and target_d >= 2 else (COST_PER_DIGIT * target_d * (1.0 if r['sigT'] == 'GREEN' else y_rate))
                    p_inv += cost
                    if r['isWinTop']:
                        p_wins += 1
                        win_m = (PAYOUT * 1.0) if not is_hc or r['winIndex'] == 0 else (PAYOUT * y_rate)
                        p_net += win_m - cost
                    else: p_net -= cost
                stats_p[str(period)] = {"profit": p_net, "invested": p_inv, "wins": p_wins, "totalRounds": p_rounds, "winrate": f"{(p_wins/p_rounds*100 if p_rounds>0 else 0):.1f}"}
                for field in ["profit", "invested", "wins", "totalRounds"]:
                    final_output["overall"][str(period)][field] += stats_p[str(period)][field]
            final_output["summary"][key] = {"domTop": ledger[0]['domTop'], "sigT": ledger[0]['sigT'], "top_digits": ledger[0]['top_digits'], "pairsT": generate_19_doors(ledger[0]['domTop']) if ledger[0]['sigT'] != 'RED' else [], "stats": stats_p, "ledger": ledger[1:11]}
        except Exception as e: print(f"⚠️ Warning {key}: {e}")

    with open(RAW_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({"lotteries": master_lottery_store}, f, ensure_ascii=False)
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False)

if __name__ == "__main__": main()
