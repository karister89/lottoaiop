import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
from datetime import datetime, timedelta

# ==========================================
# ⚙️ CONFIGURATION (2-TOP ONLY - UK/DOW TUNED)
# ==========================================
SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"

MARKETS = {
    'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG',
    'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX',
    'uk': 'FTSE', 'dow': 'DJI'
}

# 🌟 จูนค่าพิเศษเฉพาะ UK และ DOW ให้สไนเปอร์คมขึ้น
MARKET_SETTINGS = {
    'nikkei':   {'base_limit': 82, 'min_elite': 28, 'veto_mult': 1.15},
    'china':    {'base_limit': 80, 'min_elite': 30, 'veto_mult': 1.15},
    'hangseng': {'base_limit': 75, 'min_elite': 25, 'veto_mult': 1.20},
    'taiwan':   {'base_limit': 82, 'min_elite': 28, 'veto_mult': 1.15},
    'india':    {'base_limit': 78, 'min_elite': 28, 'veto_mult': 1.15},
    'germany':  {'base_limit': 82, 'min_elite': 28, 'veto_mult': 1.15},
    # ปรับบีบ UK ให้เล่นยากขึ้น + คัดบอทแม่น 30% ขึ้นไป
    'uk':       {'base_limit': 76, 'min_elite': 30, 'veto_mult': 1.25},
    # ปรับบีบ DOW หนักสุด บังคับ SKIP วันที่แกว่ง + เพิ่มเกณฑ์ความแม่น
    'dow':      {'base_limit': 68, 'min_elite': 28, 'veto_mult': 1.35}
}

BET_CONFIG = { "COST_PER_DIGIT": 19, "PAYOUT": 100 } 
BACKTEST_LOOKBACK = 90 
LEDGER_DAYS = 90 

# ==========================================
# 🧠 ALGORITHMS (2-TOP ONLY)
# ==========================================
def safe_int(val, default=0):
    try: return int(val)
    except: return default

def generate_19_doors(digit):
    if not digit: return []
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
    bots = []
    windows = [10, 18, 28, 50, 80, 130, 190, 250, 350, 500] 
    bot_id = 1
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
    creds_json = os.environ.get("GCP_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    client = gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    sheet = client.open_by_key(SHEET_ID)
    
    final_output = {
        "generatedAt": datetime.utcnow().isoformat() + "Z", "summary": {},
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

            max_idx = min(len(draws), LEDGER_DAYS + BACKTEST_LOOKBACK + 30)
            matrix = {b['id']: {'twoTop': {}} for b in BOTS} 
            for b in BOTS:
                algo_func = ALGO_MAP[b['type']]
                for i in range(max_idx):
                    subset = draws[i : i + b['window']]
                    if not subset: continue
                    matrix[b['id']]['twoTop'][i] = get_top3_digit(algo_func(subset, 'twoTop'))

            def get_eval(day_idx, m_cfg):
                limit = min(len(draws) - day_idx - 15, BACKTEST_LOOKBACK)
                hits = {b['id']: 0 for b in BOTS}
                for i in range(1, limit + 1):
                    test_idx = day_idx + i
                    actual = draws[test_idx-1]
                    for b in BOTS:
                        pT = matrix[b['id']]['twoTop'].get(test_idx)
                        if pT and pT[0]['digit'] in actual['twoTop']: hits[b['id']] += 1
                res = []
                for b in BOTS:
                    wr = (hits[b['id']] / limit) * 100 if limit > 0 else 0 
                    pwr = 3.0 if wr >= m_cfg['min_elite'] else (1.0 if wr >= 21 else (0.5 if wr >= 16 else 0))
                    res.append({**b, 'winRate': wr, 'power': pwr, 'isShadow': pwr == 0, 'status': 'elite' if wr >= m_cfg['min_elite'] else ('active' if wr >= 21 else ('probation' if wr >= 16 else 'shadow'))})
                return res

            def get_vote(day_idx, evals, m_cfg):
                vote = [0.0]*10
                for eb in evals:
                    if eb['isShadow']: continue
                    preds = matrix[eb['id']]['twoTop'].get(day_idx, [])
                    for i, r in enumerate(preds): vote[int(r['digit'])] += eb['power'] * (1 - i * 0.2)
                ranked = sorted([(str(i), vote[i]) for i in range(10)], key=lambda x: x[1], reverse=True)
                top, sec, fourth = ranked[0][1], ranked[1][1], (ranked[3][1] if len(ranked)>3 else 0)
                chaos = (fourth / top * 100) if top > 0 else 100
                
                # 🌟 แก้บั๊ก Veto ให้ดึงค่า base_limit และ veto_mult จาก MARKET_SETTINGS อย่างถูกต้อง
                is_veto = (chaos > m_cfg.get('base_limit', 82) and top > sec * m_cfg.get('veto_mult', 1.15))
                return {'digit': ranked[0][0], 'chaos': chaos, 'isVeto': is_veto}

            m_cfg = MARKET_SETTINGS.get(key, {'base_limit': 85, 'min_elite': 28})
            ledger = []
            for k in range(LEDGER_DAYS + 1):
                if k >= len(draws): break
                ev = get_eval(k, m_cfg)
                vT = get_vote(k, ev, m_cfg)
                limit = m_cfg['base_limit']
                sig_raw = 'RED' if vT['chaos'] > limit else ('YELLOW' if vT['chaos'] > (limit-15) else 'GREEN')
                
                ledger.append({
                    "date": draws[k]['date'], "actTop": draws[k]['twoTop'], "actBot": "-",
                    "open": draws[k]['open'], "diff": draws[k]['diff'], "table": draws[k]['table'],
                    "domTop": vT['digit'], "domBot": "-", "sigT": 'YELLOW' if (sig_raw == 'RED' and vT['isVeto']) else sig_raw, "sigB": "RED", "isVetoT": vT['isVeto'],
                    "isWinTop": vT['digit'] in draws[k]['twoTop'], "isWinBot": False,
                    "chaosIndex": vT['chaos'], "activeBots": sum(1 for eb in ev if not eb['isShadow']), "pairsT": generate_19_doors(vT['digit']), "pairsB": []
                })

            stats_out = {}
            for d in [30, 60, 90]:
                sub = ledger[1:d+1]; pT, wT, sT, avd, mis, cur_w, max_w, cur_l, max_l = 0,0,0,0,0,0,0,0,0
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
                cost, rev = pT * BET_CONFIG["COST_PER_DIGIT"], wT * BET_CONFIG["PAYOUT"]
                stats_out[str(d)] = {"profit": rev-cost, "invested": cost, "wins": wT, "winrate": f"{(wT/pT*100 if pT>0 else 0):.1f}", "maxWinStreak": max_w, "maxLossStreak": max_l, "avoidedLosses": avd, "missedWins": mis, "cost": cost, "rev": rev, "played": pT, "skipped": sT, "totalRounds": pT}
                final_output["overall"][str(d)]["profit"] += (rev-cost)
                final_output["overall"][str(d)]["invested"] += cost
                final_output["overall"][str(d)]["wins"] += wT
                final_output["overall"][str(d)]["totalRounds"] += pT

            curr_ev = get_eval(0, m_cfg)
            latest = ledger[0]; dt = datetime.strptime(latest['date'], "%Y-%m-%d"); nxt = dt + timedelta(days=1)
            if nxt.weekday() == 5: nxt += timedelta(days=2)
            elif nxt.weekday() == 6: nxt += timedelta(days=1)

            final_output["summary"][key] = {
                "forDate": nxt.strftime("%d/%m/%y"), "latestDate": latest['date'], "latestTop": latest['actTop'], "latestBot": "-",
                "domTop": latest['domTop'], "sigT": latest['sigT'], "isVetoT": latest['isVetoT'], "pairsT": latest['pairsT'],
                "domBot": "-", "sigB": "RED", "pairsB": [], "chaosIndex": latest['chaosIndex'], "botsCount": latest['activeBots'], "totalBots": len(BOTS),
                "ledger": ledger[1:], "stats": stats_out,
                "botSummary": {"elite": sum(1 for b in curr_ev if b['status']=='elite'), "active": sum(1 for b in curr_ev if b['status']=='active'), "probation": sum(1 for b in curr_ev if b['status']=='probation'), "shadow": sum(1 for b in curr_ev if b['status']=='shadow'), "algoCount": {a: sum(1 for b in curr_ev if b['type']==a and not b['isShadow']) for a in ALGO_MAP.keys()}, "top5": sorted([{'id': b['id'], 'name': b['name'], 'winRate': b['winRate']} for b in curr_ev], key=lambda x: x['winRate'], reverse=True)[:5], "avgWinRate": sum(b['winRate'] for b in curr_ev)/len(BOTS)}
            }
        except Exception as e: print(f"❌ Error {sheet_name}: {e}")

    for d in ["30", "60", "90"]:
        tr = final_output["overall"][d]["totalRounds"]
        final_output["overall"][d]["winrate"] = f"{(final_output['overall'][d]['wins']/tr*100 if tr>0 else 0):.2f}"

    with open('dashboard_data.json', 'w', encoding='utf-8') as f: json.dump(final_output, f, ensure_ascii=False, indent=2)
    with open('lottery-data.json', 'w', encoding='utf-8') as f: json.dump({"generatedAt": final_output["generatedAt"], "lotteries": all_lotteries_data}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__": main()
