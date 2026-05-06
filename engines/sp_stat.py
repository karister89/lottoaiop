import json
import os
import math

RAW_DATA_FILE = "../data/raw_excel.json"
OUTPUT_FILE = "../data/result_stat.json" 

def get_local_data():
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_statistics(draws):
    scores = [0.0] * 10
    lookback = 100
    subset = draws[:lookback]
    
    for i, row in enumerate(subset):
        num_str = str(row['twoTop']).zfill(2)
        if len(num_str) == 2:
            weight = math.pow(0.95, i) 
            scores[int(num_str[0])] += weight
            scores[int(num_str[1])] += weight
            
    return scores

def main():
    try:
        print("⏳ [Stat Bot] กำลังวิเคราะห์ข้อมูล...")
        draws = get_local_data()
        stat_scores = analyze_statistics(draws)
        
        ranked_digits = sorted([(str(i), s) for i, s in enumerate(stat_scores)], key=lambda x: x[1], reverse=True)
        
        result = {
            "bot_name": "Stat_Heavy_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": stat_scores,
            "status": "success"
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"✅ Stat Bot Saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
