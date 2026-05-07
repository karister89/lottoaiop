import json
import os
import glob
import math

# =====================================================================
# ⚙️ Configuration - SP Stat (Multi-Market Edition)
# =====================================================================
DATA_DIR = "../data/"

def analyze_statistics(draws):
    """
    🔻 สมการออริจินัลของพี่นพพล (Exponential Decay) 🔻
    (งวดล่าสุดได้น้ำหนักเยอะสุด ยิ่งเก่ายิ่งถูกลดความสำคัญลง)
    """
    scores = [0.0] * 10
    lookback = 100
    subset = draws[:lookback]
    
    for i, row in enumerate(subset):
        # ใช้ .get() เพื่อกันกระแทกกรณีเจอแถวที่ไม่มีข้อมูล twoTop
        two_top = row.get('twoTop', '')
        if not two_top:
            continue
            
        num_str = str(two_top).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
            weight = math.pow(0.95, i) 
            scores[int(num_str[0])] += weight
            scores[int(num_str[1])] += weight
            
    return scores

def main():
    print("⏳ [SP Stat] เริ่มต้นวิเคราะห์สถิติความถี่และน้ำหนัก (Multi-Market)...")
    
    # 🔍 สแกนหาไฟล์ raw_ ทั้งหมด
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    if not raw_files:
        print("❌ [SP Stat] ไม่พบไฟล์ข้อมูลดิบ (raw_*.json)!")
        return

    # 🔄 วนลูปอ่านข้อมูลทีละหุ้น
    for file_path in raw_files:
        
        # 🛑 ดักจับไฟล์ขยะ!
        if "raw_excel.json" in file_path:
            continue
            
        # ปอกเปลือกเอาชื่อหุ้นออกมา (เช่น raw_nikkei.json -> nikkei)
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)

            if not draws or len(draws) == 0:
                print(f"⚠️ ตลาด {market_name} ไม่มีข้อมูล ข้าม...")
                continue

            print(f"📊 กำลังคำนวณสถิติหุ้น: {market_name.upper()}")
            
            # ส่งข้อมูลไปเข้าสมการของพี่
            stat_scores = analyze_statistics(draws)
            
            # จัดอันดับตัวเลข
            ranked_digits = sorted([(str(i), s) for i, s in enumerate(stat_scores)], key=lambda x: x[1], reverse=True)
            
            # จัดเตรียมแพ็กเกจข้อมูล (เพิ่ม field "market" เข้าไป)
            result = {
                "bot_name": "Stat_Heavy_V1",
                "market": market_name,
                "top_digits": [r[0] for r in ranked_digits],
                "raw_scores": stat_scores,
                "status": "success"
            }
            
            # 💾 บันทึกไฟล์แยกตามชื่อหุ้น เช่น result_stat_nikkei.json
            out_file = os.path.join(DATA_DIR, f"result_stat_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
                
            print(f"  ✅ บันทึกผลสำเร็จ -> result_stat_{market_name}.json")
            
        except Exception as e:
            print(f"❌ Error ตอนคำนวณตลาด {market_name}: {e}")

    print("🎉 [SP Stat] วิเคราะห์เสร็จสิ้นครบทุกตลาด!")

if __name__ == "__main__":
    main()
