import json
import os
import pandas as pd

RAW_DATA_FILE = "../data/raw_excel.json"
OUTPUT_FILE = "../data/result_market.json" 

def get_local_data():
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_market(draws):
    scores = [0.0] * 10
    df = pd.DataFrame(draws)
    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    current_diff = df.iloc[0]['diff'] 
    
    if current_diff > 0:
        past_matches = df[df['diff'] > 0].head(100)
    else:
        past_matches = df[df['diff'] <= 0].head(100)

    for _, row in past_matches.iterrows():
        num_str = str(row['twoTop']).zfill(2)
        if len(num_str) == 2:
            scores[int(num_str[0])] += 1.0 
            scores[int(num_str[1])] += 1.0 

    current_open_last_digit = str(df.iloc[0]['open'])[-1]
    if current_open_last_digit.isdigit():
        scores[int(current_open_last_digit)] += 1.5 

    return scores

def main():
    try:
        print("⏳ [Market Bot] กำลังวิเคราะห์ข้อมูล...")
        draws = get_local_data()
        market_scores = analyze_market(draws)
        
        ranked_digits = sorted([(str(i), s) for i, s in enumerate(market_scores)], key=lambda x: x[1], reverse=True)
        
        result = {
            "bot_name": "Market_Whale_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": market_scores,
            "status": "success"
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"✅ Market Bot Saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
