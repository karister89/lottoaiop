import json
import os
import glob

# =====================================================================
# ⚖️ Configuration - Consensus Aggregator (V3 Split + Dynamic Weights)
# =====================================================================
DATA_DIR = "data"
WEIGHTS_FILE = os.path.join(DATA_DIR, "dynamic_weights.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "bot_consensus_votes.json")

def main():
    print("\n" + "="*75)
    print("⏳ [Aggregator] รวบรวมผลโหวตและคูณน้ำหนักความเก่ง (Weighted Consensus)...")
    print("="*75)
    
    # 1. โหลดสมุดพกคะแนน (Weight) ที่ได้จาก core_weight_eval.py
    try:
        with open(WEIGHTS_FILE, 'r', encoding='utf-8') as f:
            weight_data = json.load(f)
    except Exception as e:
        print(f"⚠️ ไม่พบไฟล์ weights ({e}) - จะใช้น้ำหนักเท่ากันหมดแทน")
        weight_data = {"markets": {}}

    master_votes = {}
    result_files = glob.glob(os.path.join(DATA_DIR, "result_*.json"))
    
    if not result_files:
        print("❌ Error: ไม่พบผลลัพธ์จากบอท (result_*.json) ใน data folder!")
        return

    for file_path in result_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            market = data.get('market')
            bot_name = data.get('bot_name', '').lower()
            
            # แปลงชื่อบอทให้ตรงกับคีย์ในไฟล์ weight
            if "ai" in bot_name: b_key = "ai"
            elif "market" in bot_name: b_key = "market"
            elif "math" in bot_name: b_key = "math"
            elif "stat" in bot_name: b_key = "stat"
            else: b_key = bot_name

            if not market: continue
            
            if market not in master_votes:
                master_votes[market] = {
                    "front": {str(i): 0.0 for i in range(10)},
                    "back": {str(i): 0.0 for i in range(10)}
                }
            
            # ดึง Weight ของตลาดนี้ (ถ้าไม่มีข้อมูลให้คะแนน 0.25)
            market_weights = weight_data.get('markets', {}).get(market, {}).get('weights', {})
            weight_front = market_weights.get('front', {}).get(b_key, 0.25)
            weight_back = market_weights.get('back', {}).get(b_key, 0.25)

            # 🗳️ นับโหวตหลักสิบ (Front) - เอาเลขที่บอทเลือกมาบวกด้วยคะแนนความเก่ง
            for digit in data.get('top_front', []):
                master_votes[market]['front'][str(digit)] += weight_front
                
            # 🗳️ นับโหวตหลักหน่วย (Back) - เอาเลขที่บอทเลือกมาบวกด้วยคะแนนความเก่ง
            for digit in data.get('top_back', []):
                master_votes[market]['back'][str(digit)] += weight_back
                
        except Exception as e:
            print(f"⚠️ Warning: ข้ามไฟล์ {file_path} เนื่องจาก Error: {e}")

    # 💾 บันทึกผลโหวตลงไฟล์ตารางคะแนน เพื่อส่งต่อให้แม่ทัพ (Optimizer)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_votes, f, ensure_ascii=False, indent=4)
        
    print(f"✅ ประมวลผลโหวตสำเร็จ! ส่งต่อตารางคะแนน bot_consensus_votes.json เรียบร้อย\n")

if __name__ == "__main__":
    main()
