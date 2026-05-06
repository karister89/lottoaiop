import json
import os

RAW_DATA_FILE = "../data/raw_excel.json"
OUTPUT_FILE = "../data/result_math.json" 

def get_local_data():
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_math(draws):
    scores = [0.0] * 10
    last_seen = {i: 0 for i in range(10)}
    found = {i: False for i in range(10)}
    
    for gap, row in enumerate(draws):
        num_str = str(row['twoTop']).zfill(2)
        if len(num_str) == 2:
            d1, d2 = int(num_str[0]), int(num_str[1])
            if not found[d1]:
                last_seen[d1] = gap
                found[d1] = True
            if not found[d2]:
                last_seen[d2] = gap
                found[d2] = True
        if all(found.values()): break

    for i in range(10):
        scores[i] += last_seen[i] * 0.5 

    for i in range(10):
        counts = 0
        for row in draws[:50]:
            if str(i) in str(row['twoTop']).zfill(2):
                counts += 1
        if 8 <= counts <= 12: 
            scores[i] += 10.0

    return scores

def main():
    try:
        print("⏳ [Math Bot] กำลังวิเคราะห์ข้อมูล...")
        draws = get_local_data()
        math_scores = analyze_math(draws)
        
        ranked_digits = sorted([(str(i), s) for i, s in enumerate(math_scores)], key=lambda x: x[1], reverse=True)
        
        result = {
            "bot_name": "Math_Probability_V1",
            "top_digits": [r[0] for r in ranked_digits],
            "raw_scores": math_scores,
            "status": "success"
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"✅ Math Bot Saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
