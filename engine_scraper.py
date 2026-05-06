import gspread
from google.oauth2.service_account import Credentials
import json
import os
import math
from datetime import datetime

# ======================================================================
# ⚙️ แผงควบคุมหลัก (CONTROL PANEL) - Sovereign Engine V2.5
# ======================================================================

COST_PER_DIGIT = 19             
PAYOUT = 100                    

DEFAULT_BASE_LIMIT = 80         
DEFAULT_MIN_ELITE = 39          
DEFAULT_TARGET_DIGITS = 2       
DEFAULT_YELLOW_RATE = 0.5       
DEFAULT_HC_MODE = True          

SHEET_ID = "1xc4B2mhrC1VdUfOuZUhVQbDyzbSk0J4jCru9am_iLzA"
RAW_DATA_FILE = 'data_raw.json'          
DASHBOARD_FILE = 'data_dashboard.json'  
SETTINGS_FILE = 'config_markets.json'    

MARKETS = {
    'nikkei': 'NIKKEI', 'china': 'SHE', 'hangseng': 'HANGSENG', 
    'taiwan': 'TPE', 'india': 'SENSEX', 'germany': 'DAX', 
    'uk': 'FTSE', 'dow': 'DJI'
}

# ======================================================================
# 🤖 ระบบประมวลผล (Core Logic)
# ======================================================================

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def safe_int(v, d=0):
    try: return int(v)
    except: return d

def generate_19_doors(digit):
    if not digit or digit == "-": return []
    return sorted(list(set([f"{digit}{i}" for i in range(10)] + [f"{i}{digit}" for i in range(10)])))

def get_bots_master():
    blist = []
    windows = [10, 18, 28, 50, 80, 130, 190, 250, 350, 500]
    bot_id = 1
    for w in windows:
        blist.append({'id': f"B{bot_id:03d}", 'window': w})
        bot_id += 1
    return blist

def main():
    creds_json = os.environ.get("GCP_CREDENTIALS")
    if not creds_json: 
        print("❌ Error: ไม่พบ GCP_CREDENTIALS")
        return
        
    client = gspread.authorize(Credentials.from_service_account_info(json.loads(creds_json), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]))
    sheet = client.open_by_key(SHEET_ID)
    
    settings = load_settings()
    final_output = {
        "generatedAt": datetime.utcnow().isoformat() + "Z", 
        "summary": {}, 
        "overall": { d: {"profit": 0, "invested": 0, "wins": 0, "totalRounds": 0} for d in ["30", "60", "90"] }
    }
    master_lottery_store = {}
    BOTS_LIST = get_bots_master()

    for key, sheet_name in MARKETS.items():
        try:
            ws = sheet.worksheet(sheet_name)
            all_rows = ws.get_all_values()[2:] # ข้ามหัวตาราง 2 แถว
            
            draws = []
            for r in all_rows:
                if not r or not r[0] or len(r) < 4: continue
                # r[0]=วันที่, r[3]=2ตัวบน
                draws.append({
                    "date": r[0], 
                    "twoTop": r[3].strip().zfill(2) if r[3] else "",
                    "open": float(r[1]) if r[1] else 0,
                    "diff": float(r[2]) if r[2] else 0
                })
            
            # 🌟 จุดสำคัญ: กลับหัวข้อมูลเพื่อให้วันที่ล่าสุด (2026) มาอยู่ตำแหน่งแรก
            draws.reverse() 
            master_lottery_store[key] = draws
            
            cfg = settings.get(key, {})
            target_d = cfg.get('target_digits', DEFAULT_TARGET_DIGITS)
            y_rate = cfg.get('yellow_bet_rate', DEFAULT_YELLOW_RATE)
            is_hc = cfg.get('hardcore_mode', DEFAULT_HC_MODE)
            base_limit = cfg.get('base_limit', DEFAULT_BASE_LIMIT)
            min_elite = cfg.get('min_elite', DEFAULT_MIN_ELITE)
            
            ledger = []
            # คำนวณย้อนหลัง 92 งวด (เริ่มจากปัจจุบันถอยหลังไป)
            for k in range(min(len(draws)-1, 92)):
                vote = [0.0]*10
                for b in BOTS_LIST:
                    lookback = 60
                    hits = 0
                    # เช็ก Win-rate บอทย้อนหลัง (เลื่อนตามตำแหน่ง k)
                    for i in range(1, lookback + 1):
                        idx = k + i
                        if idx + b['window'] >= len(draws): continue
                        
                        sub = draws[idx : idx + b['window']]
                        sc = [0.0]*10
                        for si, sd in enumerate(sub):
                            v = sd.get('twoTop', "")
                            if len(v) == 2:
                                w = math.exp(-si/15.0) * 1.5
                                sc[safe_int(v[0])] += w; sc[safe_int(v[1])] += w
                        
                        top_pred = str(sc.index(max(sc)))
                        if top_pred in draws[idx-1]['twoTop']: hits += 1
                    
                    wr = (hits/lookback*100) if lookback > 0 else 0
                    # เฉพาะบอทที่สอบผ่านเกณฑ์ Elite ถึงจะมีสิทธิ์โหวต
                    if wr >= min_elite:
                        sub_now = draws[k+1 : k+1+b['window']]
                        sc_now = [0.0]*10
                        for si, sd in enumerate(sub_now):
                            v = sd.get('twoTop', "")
                            if len(v) == 2:
                                w = math.exp(-si/15.0) * 1.5
                                sc_now[safe_int(v[0])] += w; sc_now[safe_int(v[1])] += w
                        vote[sc_now.index(max(sc_now))] += 3.0

                ranked_v = sorted([(str(x), v) for x, v in enumerate(vote)], key=lambda x: x[1], reverse=True)
                top_v = ranked_v[0][1]
                fourth_v = ranked_v[3][1] if len(ranked_v) > 3 else 0
                chaos = (fourth_v / top_v * 100) if top_v > 0 else 100
                
                # ตัดเกรดสัญญาณไฟจากพารามิเตอร์ที่ Optimize มาแล้ว
                sig = 'RED' if top_v == 0 else ('YELLOW' if chaos > base_limit else 'GREEN')
                
                played = [r[0] for r in ranked_v[:target_d]]
                win_idx = next((i for i, d in enumerate(played) if d in draws[k]['twoTop']), -1)
                
                ledger.append({
                    "date": draws[k]['date'], 
                    "sigT": sig, 
                    "isWinTop": (win_idx != -1), 
                    "winIndex": win_idx, 
                    "top_digits": [r[0] for r in ranked_v], 
                    "domTop": ranked_v[0][0]
                })

            # คำนวณสถิติสรุป 30, 60, 90 วัน
            stats_p = {}
            for period in [30, 60, 90]:
                p_net, p_inv, p_wins, p_rounds = 0, 0, 0, 0
                # ใช้ข้อมูลล่าสุด (ledger index ต้นๆ)
                for r in ledger[:period]:
                    if r['sigT'] == 'RED': continue
                    p_rounds += 1
                    # คำนวณต้นทุนแบบ Hardcore Support
                    cost = (COST_PER_DIGIT * 1.0) + (COST_PER_DIGIT * y_rate) if is_hc and r['sigT'] == 'YELLOW' and target_d >= 2 else (COST_PER_DIGIT * target_d * (1.0 if r['sigT'] == 'GREEN' else y_rate))
                    p_inv += cost
                    if r['isWinTop']:
                        p_wins += 1
                        win_m = (PAYOUT * 1.0) if not is_hc or r['winIndex'] == 0 else (PAYOUT * y_rate)
                        p_net += win_m - cost
                    else: p_net -= cost
                
                stats_p[str(period)] = {
                    "profit": round(p_net, 2), 
                    "invested": round(p_inv, 2), 
                    "wins": p_wins, 
                    "totalRounds": p_rounds, 
                    "winrate": f"{(p_wins/p_rounds*100 if p_rounds>0 else 0):.1f}"
                }
                for field in ["profit", "invested", "wins", "totalRounds"]:
                    final_output["overall"][str(period)][field] += stats_p[str(period)][field]

            final_output["summary"][key] = {
                "domTop": ledger[0]['domTop'], 
                "sigT": ledger[0]['sigT'], 
                "top_digits": ledger[0]['top_digits'], 
                "target_digits": target_d,
                "pairsT": generate_19_doors(ledger[0]['domTop']) if ledger[0]['sigT'] != 'RED' else [], 
                "stats": stats_p, 
                "ledger": ledger[:10] # โชว์ 10 งวดล่าสุดในหน้าเว็บ
            }
            
        except Exception as e:
            print(f"⚠️ Warning {key}: {e}")

    # บันทึกข้อมูล
    with open(RAW_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({"lotteries": master_lottery_store}, f, ensure_ascii=False)
    
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False)
        
    print(f"✅ Scraper v2.5 Updated: Data sorted by newest date.")

if __name__ == "__main__":
    main()
