import json
import os

# ⚙️ Configuration
DATA_DIR = "../data/"
OUTPUT_FILE = "../data/final_synergy.json"

def load_json(filename):
    """ฟังก์ชันสำหรับโหลดผลลัพธ์จากบอททั้ง 4 สาย"""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"⚠️ Warning: ไม่พบไฟล์ {filename}")
        return None

def main():
    print("🧠 Starting Sovereign Synergy Engine...")
    
    # 1. รวบรวมข้อมูลจากบอท Specialist
    market_data = load_json("result_market.json")
    stat_data = load_json("result_stat.json")
    math_data = load_json("result_math.json")
    ai_data = load_json("result_ai.json")
    
    total_scores = [0.0] * 10
    
    # 2. กำหนดค่าน้ำหนัก (Weighting Strategy)
    # สามารถปรับเปลี่ยนได้ตามสถานการณ์ตลาด
    weights = {
        "market": 0.30,  # ให้ความสำคัญกับทิศทางตลาด (Open/Diff) 30%
        "stat": 0.25,    # ความแรงของสถิติปัจจุบัน 25%
        "math": 0.25,    # ความอั้นและความเสถียร 25%
        "ai": 0.20       # ประวัติศาสตร์ซ้ำรอย 20%
    }
    
    def apply_scores(bot_data, weight):
        if bot_data and "raw_scores" in bot_data:
            for i in range(10):
                # เอาคะแนนดิบของบอท มาคูณกับเปอร์เซ็นต์น้ำหนัก
                total_scores[i] += bot_data["raw_scores"][i] * weight

    # ผสานคะแนนจากทุกสายเข้าด้วยกัน
    apply_scores(market_data, weights["market"])
    apply_scores(stat_data, weights["stat"])
    apply_scores(math_data, weights["math"])
    apply_scores(ai_data, weights["ai"])
    
    # 3. จัดอันดับตัวเลขที่ "เสถียรและซัพพอร์ตกันที่สุด"
    ranked_digits = sorted(
        [(str(i), s) for i, s in enumerate(total_scores)], 
        key=lambda x: x[1], 
        reverse=True
    )
    
    # คัดเลือกชุดตัวเลขเพื่อนำไปใช้งาน
    primary_pair = [ranked_digits[0][0], ranked_digits[1][0]] # ตัวเด่น 2 ตัวแรก
    support_digit = ranked_digits[2][0] # ตัวรอง (เอาไว้กันพัง)
    
    # 4. สร้าง Report สรุปผล
    final_result = {
        "system_status": "Sovereign V3 Online",
        "primary_pair": primary_pair,
        "support_digit": support_digit,
        "synergy_scores": total_scores,
        "weights_used": weights
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Synergy Optimization Complete.")
    print(f"🎯 ชุดเลขหลัก (Primary): {primary_pair}")
    print(f"🛡️ เลขตัวรอง (Support): {support_digit}")
    print(f"📁 บันทึกผลลัพธ์ที่: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
