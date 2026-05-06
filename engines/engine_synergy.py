import json
import os

DATA_DIR = "../data/"
OUTPUT_FILE = "../data/final_synergy.json"

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def main():
    print("🧠 Starting Sovereign Synergy Engine...")
    
    market_data = load_json("result_market.json")
    stat_data = load_json("result_stat.json")
    math_data = load_json("result_math.json")
    ai_data = load_json("result_ai.json")
    
    total_scores = [0.0] * 10
    
    weights = {
        "market": 0.30,
        "stat": 0.25,
        "math": 0.25,
        "ai": 0.20
    }
    
    def apply_scores(bot_data, weight):
        if bot_data and "raw_scores" in bot_data:
            for i in range(10):
                total_scores[i] += bot_data["raw_scores"][i] * weight

    apply_scores(market_data, weights["market"])
    apply_scores(stat_data, weights["stat"])
    apply_scores(math_data, weights["math"])
    apply_scores(ai_data, weights["ai"])
    
    ranked_digits = sorted([(str(i), s) for i, s in enumerate(total_scores)], key=lambda x: x[1], reverse=True)
    
    primary_pair = [ranked_digits[0][0], ranked_digits[1][0]]
    support_digit = ranked_digits[2][0]
    
    final_result = {
        "system_status": "Sovereign V3 Online",
        "primary_pair": primary_pair,
        "support_digit": support_digit,
        "synergy_scores": total_scores,
        "weights_used": weights
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Synergy Complete. 🎯 หลัก: {primary_pair} | 🛡️ รอง: {support_digit}")

if __name__ == "__main__":
    main()
