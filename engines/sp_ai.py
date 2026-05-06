import json
import os
import pandas as pd

RAW_DATA_FILE = "../data/raw_excel.json"
OUTPUT_FILE = "../data/result_ai.json" 

def get_local_data():
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_pattern(draws):
    scores = [0.0] * 10
    df = pd.DataFrame(draws)
    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    current_diff = df.iloc[0]['diff']
    
    df['distance'] = abs(df['diff'] - current_diff)
    similar_past = df.iloc[1:].sort_values(by='distance').head(30)
    
    for index, row in similar_past.iterrows():
        num_str = str(row['twoTop']).zfill(2)
        weight = 1.0 / (row['distance'] + 0.1) 
        if len(num_str) == 2:
            scores[int(num_str[0])] += weight
            scores[int(num_str[1])] += weight

    return scores

def main():
    try:
        print("⏳ [AI Bot] กำลังวิเคราะห์แพทเทิร์น...")
        draws = get_local_data()
        ai_scores = analyze_pattern(draws)
        
        ranked_digits = sorted([(str(i), s) for i, s in enumerate(ai_scores)], key=lambda x: x[1], reverse=True)
        
        result = {
            "bot_name": "AI_Pattern_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": ai_scores,
            "status": "success"
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"✅ AI Bot Saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
