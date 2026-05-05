import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
from datetime import datetime, timedelta

# ==========================================
# ⚙️ CONFIGURATION (AUTO-PILOT SCRAPER V2.5)
# ==========================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"

MARKETS = {
    'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG',
    'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX',
    'uk': 'FTSE', 'dow': 'DJI'
}

BET_CONFIG = { "COST_PER_DIGIT": 19, "PAYOUT": 100 } 
BACKTEST_LOOKBACK = 90 
LEDGER_DAYS = 90 

# โหลดค่า Settings (ถ้ามี) หรือใช้ค่า Default
try:
    with open('market_settings.json', 'r', encoding='utf-8') as f:
        MARKET_SETTINGS = json.load(f)
        print("✅ โหลดค่า Parameters จาก market_settings.json สำเร็จ")
except:
    print("⚠️ ไม่พบไฟล์ settings กำลังใช้ค่าพื้นฐาน (รูด 2 ตัว)")
    MARKET_SETTINGS = {k: {'base_limit': 80, 'min_elite': 28, 'veto_mult': 1.20, 'target_digits': 2} for k in MARKETS.keys()}

def safe_int(val, default=0):
    try: return int(val)
    except: return default

def generate_19_doors(digit):
    if not digit or digit == "-": return []
    return sorted(list(set([f"{digit}{i}" for i in range(10)] + [f"{i}{digit}" for i in range(10)])))

# --- ALGORITHMS ---
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
    blist = []
    windows = [10, 18, 28, 50, 80, 130, 190, 250, 350, 500] 
    bot_id = 1
    for w in windows:
        for algo in ALGO_MAP.keys():
            blist.append({'id': f"B{bot_id:03d}", 'type': algo, 'window': w, 'name': f"{algo.upper()}-{w}"})
            bot_id += 1
    return blist

MASTER_BOTS = build_bots()

def get_top_digits_list(scores):
    ranked = sorted([{'digit': str(i), 'score': scores[i]} for i in range(10)], key=lambda x: x['score'], reverse=True)
    return [r['digit'] for r in ranked]

def main():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json:
        print("❌ Error: Missing GCP_CREDENTIALS")
        return

    creds_dict = json.loads(creds_json)
    client = gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    sheet = client.open_by_key(SHEET_ID)
    
    final_output = {
        "generatedAt": datetime.utcnow().isoformat() + "Z", 
        "summary": {},
        "overall": { d: {"profit": 0, "invested": 0, "wins": 0, "totalRounds": 0} for d in ["30", "60", "90"] }
    }
    all_lotteries_data = {}

    for key, sheet_name in MARKETS.items():
        try:
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
            all_lotteries_data[key] = draws
            if len(draws) < 30: continue

            m_cfg = MARKET_SETTINGS.get(key, {'base_limit': 80, 'min_elite': 28, 'veto_mult': 1.20, 'target_digits': 2})
            is_auto_skip = m_cfg.get('base_limit') == -1

            max_idx = min(len(draws), LEDGER_DAYS + BACKTEST_LOOKBACK + 30)
            matrix = {b['id']: {'twoTop': {}} for b in MASTER_BOTS} 
            for b in MASTER_BOTS:
                algo_func = ALGO_MAP[b['type']]
                for i in range(max_idx):
                    subset = draws[i : i + b['window']]
                    if not subset: continue
                    matrix[b['id']]['twoTop'][i] = get_top_digits_list(algo_func(subset, 'twoTop'))

            def get_eval(day_idx, m_cfg):
                if is_auto_skip: return [{'id': b['id'], 'winRate': 0, 'power': 0, 'isShadow': True, 'status': 'shadow'} for b in MASTER_BOTS]
                limit = min(len(draws) - day_idx - 15, BACKTEST_LOOKBACK)
                hits = {b['id']: 0 for b in MASTER_BOTS}
                for i in range(1, limit + 1):
                    test_idx = day_idx + i
                    if test_idx >= len(draws): continue
                    actual = draws[test_idx-1]
                    for b in MASTER_BOTS:
                        p_list = matrix[b['id']]['twoTop'].get(test_idx)
                        if p_list and p_list[0] in actual['twoTop']: hits[b['id']] += 1
                res = []
                for b in MASTER_BOTS:
                    wr = (hits[b['id']] / limit) * 100 if limit > 0 else 0 
                    pwr = 3.0 if wr >= m_cfg['min_elite'] else (1.0 if wr >= 21 else (0.5 if wr >= 16 else 0))
                    res.append({**b, 'winRate': wr, 'power': pwr, 'isShadow': pwr == 0, 'status': 'elite' if wr >= m_cfg['min_elite'] else ('active' if wr >= 21 else ('probation' if wr >= 16 else 'shadow'))})
                return res

            def get_vote(day_idx, evals, m_cfg):
                if is_auto_skip: return {'digit': '-', 'chaos': 100, 'isVeto': False, 'top_digits': ["-"]*5}
                vote = [0.0]*10
                for eb in evals:
                    if eb['isShadow']: continue
                    preds = matrix[eb['id']]['twoTop'].get(day_idx, [])
                    # ให้คะแนน 3 อันดับแรกของแต่ละบอท
                    for i, dgt in enumerate(preds[:3]): 
                        vote[int(dgt)] += eb['power'] * (1 - i * 0.2)
                
                ranked = sorted([(str(i), vote[i]) for i in range(10)], key=lambda x: x[1], reverse=True)
                top, sec, fourth = ranked[0][1], ranked[1][1], (ranked[3][1] if len(ranked)>3 else 0)
                chaos = (fourth / top * 100) if top > 0 else 100
                is_veto = (chaos > m_cfg.get('base_limit', 82) and top > sec * m_cfg.get('veto_mult', 1.15))
                return {'digit': ranked[0][0], 'chaos': chaos, 'isVeto': is_veto, 'top_digits': [r[0] for r in ranked[:5]]}

            ledger_data_list = []
            for k in range(LEDGER_DAYS + 1):
                if k >= len(draws): break
                ev = get_eval(k, m_cfg)
                vT = get_vote(k, ev, m_cfg)
                
                # ตรวจสอบการชนะตามจำนวนที่ตั้งไว้ (2 หรือ 5)
                target_d = m_cfg.get('target_digits', 2)
                played_digits = vT['top_digits'][:target_d]
                isWinTop = any(d in draws[k]['twoTop'] for d in played_digits) if not is_auto_skip else False
                
                limit = m_cfg['base_limit']
                sig_raw = 'RED' if vT['chaos'] > limit else ('YELLOW' if vT['chaos'] > (limit-15) else 'GREEN')
                final_sig = 'YELLOW' if (sig_raw == 'RED' and vT['isVeto']) else sig_raw
                if is_auto_skip: final_sig = 'RED'

                ledger_data_list.append({
                    "date": draws[k]['date'], "actTop": draws[k]['twoTop'],
                    "open": draws[k]['open'], "diff": draws[k]['diff'], "table": draws[k]['table'],
                    "domTop": vT['digit'], "top_digits": vT['top_digits'], "sigT": final_sig,
                    "isWinTop": isWinTop, "chaosIndex": vT['chaos'], "activeBots": sum(1 for eb in ev if not eb['isShadow']),
                    "pairsT": generate_19_doors(vT['digit']) if final_sig != 'RED' else []
                })

            # คำนวณสถิติ 30/60/90
            stats_out = {}
            target_d = m_cfg.get('target_digits', 2)
            cost_per_round = BET_CONFIG["COST_PER_DIGIT"] * target_d # ทุนวิ่งตามจำนวนเลข (2 ตัว=38, 5 ตัว=95)

            for d_period in [30, 60, 90]:
                sub = ledger_data_list[1:d_period+1]
                pT, wT, sT, avd, mis, cur_w, max_w, cur_l, max_l = 0,0,0,0,0,0,0,0,0
                for r in reversed(sub):
                    if r['sigT'] != 'RED':
                        pT += 1
                        if r['isWinTop']: wT += 1; cur_w += 1; cur_l = 0
                        else: cur_l += 1; cur_w = 0
                        max_w, max_l = max(max_w, cur_w), max(max_l, cur_l)
                    else:
                        sT += 1
                        if not r['isWinTop']: avd += 1
                        else: mis += 1
                
                cost, rev = pT * cost_per_round, wT * BET_CONFIG["PAYOUT"]
                stats_out[str(d_period)] = {
                    "profit": rev-cost, "invested": cost, "wins": wT, 
                    "winrate": f"{(wT/pT*100 if pT>0 else 0):.1f}", "totalRounds": pT,
                    "maxWinStreak": max_w, "maxLossStreak": max_l, "avoidedLosses": avd, "missedWins": mis
                }
                
                # สะสมลง Overall
                final_output["overall"][str(d_period)]["profit"] += (rev-cost)
                final_output["overall"][str(d_period)]["invested"] += cost
                final_output["overall"][str(d_period)]["wins"] += wT
                final_output["overall"][str(d_period)]["totalRounds"] += pT

            latest = ledger_data_list[0]
            final_output["summary"][key] = {
                "latestDate": latest['date'], "latestTop": latest['actTop'],
                "domTop": latest['domTop'], "top_digits": latest['top_digits'], "sigT": latest['sigT'],
                "chaosIndex": latest['chaosIndex'], "botsCount": latest['activeBots'], "totalBots": len(MASTER_BOTS),
                "ledger": ledger_data_list[1:], "stats": stats_out
            }
        except Exception as e: print(f"❌ Error {sheet_name}: {e}")

    # คำนวณ % Win Rate รวม
    for d in ["30", "60", "90"]:
        ov = final_output["overall"][d]
        tr = ov["totalRounds"]
        ov["winrate"] = f"{(ov['wins']/tr*100 if tr>0 else 0):.2f}"

    with open('dashboard_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    with open('lottery-data.json', 'w', encoding='utf-8') as f:
        json.dump({"generatedAt": final_output["generatedAt"], "lotteries": all_lotteries_data}, f, ensure_ascii=False, indent=2)
    print("✅ scraper.py อัปเดตข้อมูลสำเร็จ!")

if __name__ == "__main__":
    main()
