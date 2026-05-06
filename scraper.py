import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
from datetime import datetime, timedelta

SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
MARKETS = {'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG', 'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX', 'uk': 'FTSE', 'dow': 'DJI'}
BET_CONFIG = { "COST_PER_DIGIT": 19, "PAYOUT": 100 } 

try:
    with open('market_settings.json', 'r', encoding='utf-8') as f: MARKET_SETTINGS = json.load(f)
except: MARKET_SETTINGS = {}

def get_market_config(key):
    return MARKET_SETTINGS.get(key, {'base_limit': 80, 'min_elite': 28, 'target_digits': 2, 'yellow_bet_rate': 0.5, 'hardcore_mode': False})

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
    
    final_output = {"generatedAt": datetime.utcnow().isoformat() + "Z", "summary": {}, "overall": { d: {"profit": 0, "invested": 0, "wins": 0, "totalRounds": 0} for d in ["30", "60", "90"] }}

    for key, sheet_name in MARKETS.items():
        try:
            ws = sheet.worksheet(sheet_name)
            rows = ws.get_all_values()[2:]
            draws = []
            for r in rows:
                if not r or not r[0]: continue
                r += [""]*9
                draws.append({"date": r[0], "twoTop": r[3].strip().zfill(2) if r[3] else ""})
            
            cfg = get_market_config(key)
            target_d = cfg['target_digits']
            y_rate = cfg['yellow_bet_rate']
            is_hc = cfg.get('hardcore_mode', False)
            
            ledger = []
            for k in range(92):
                if k+1 >= len(draws): break
                scores = algo_hybrid(draws[k+1:k+31], 'twoTop')
                top_list = get_top_digits(scores)
                
                chaos = (k % 35) + 45 
                sig = 'GREEN' if chaos < 70 else 'YELLOW'
                if k % 12 == 0: sig = 'RED'
                
                played = top_list[:target_d]
                is_win = False
                win_idx = -1
                for idx_p, d in enumerate(played):
                    if d in draws[k]['twoTop']:
                        is_win = True
                        win_idx = idx_p
                        break
                
                ledger.append({"date": draws[k]['date'], "sigT": sig, "isWinTop": is_win, "winIndex": win_idx, "top_digits": top_list, "domTop": top_list[0]})

            stats_30_60_90 = {}
            base_cost = BET_CONFIG["COST_PER_DIGIT"] * target_d
            
            for period in [30, 60, 90]:
                net_p, net_i, wins, rounds = 0, 0, 0, 0
                for r in ledger[1:period+1]: 
                    if r['sigT'] == 'RED': continue
                    rounds += 1
                    
                    if is_hc and r['sigT'] == 'YELLOW' and target_d >= 2:
                        cost = (19 * 1.0) + (19 * y_rate)
                        net_i += cost
                        if r['isWinTop']:
                            wins += 1
                            if r['winIndex'] == 0: net_p += (BET_CONFIG["PAYOUT"] * 1.0) - cost
                            elif r['winIndex'] == 1: net_p += (BET_CONFIG["PAYOUT"] * y_rate) - cost
                        else: net_p -= cost
                    else:
                        current_rate = 1.0 if r['sigT'] == 'GREEN' else y_rate
                        cost = base_cost * current_rate
                        net_i += cost
                        if r['isWinTop']:
                            wins += 1
                            net_p += (BET_CONFIG["PAYOUT"] * current_rate) - cost
                        else: net_p -= cost
                
                stats_30_60_90[str(period)] = {"profit": net_p, "invested": net_i, "wins": wins, "totalRounds": rounds, "winrate": f"{(wins/rounds*100 if rounds>0 else 0):.1f}"}
                final_output["overall"][str(period)]["profit"] += net_p
                final_output["overall"][str(period)]["invested"] += net_i
                final_output["overall"][str(period)]["wins"] += wins
                final_output["overall"][str(period)]["totalRounds"] += rounds

            final_output["summary"][key] = {"domTop": ledger[0]['domTop'], "sigT": ledger[0]['sigT'], "top_digits": ledger[0]['top_digits'], "pairsT": generate_19_doors(ledger[0]['domTop']) if ledger[0]['sigT'] != 'RED' else [], "stats": stats_30_60_90, "ledger": ledger[1:11]}
            
        except Exception as e: print(f"❌ Error {key}: {e}")

    with open('dashboard_data.json', 'w', encoding='utf-8') as f: json.dump(final_output, f, ensure_ascii=False)

if __name__ == "__main__": main()
