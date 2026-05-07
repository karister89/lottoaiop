import json
import os
import glob

# =====================================================================
# ⚙️ Configuration - SP Math (Multi-Market Edition)
# =====================================================================
DATA_DIR = "../data/"

def analyze_math(draws):
    """
    🔻 สมการออริจินัลของพี่นพพล (Gap Analysis & Sweet Spot) 🔻
    """
    scores = [0.0] * 10
    last_seen = {i: 0 for i in range(10)}
    found = {i: False for i in range(10)}
    
    # 1. หาระยะห่าง (Gap) ของเลขแต่ละตัว
    for gap, row in enumerate(draws):
        # กันกระแทกกรณีเจอแถวว่าง
        two_top = row.get('twoTop', '')
        if not two_top:
            continue
            
        num_str = str(two_top).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
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

    # 2. หาความถี่ในจุดสมดุล (8-12 ครั้ง ใน 50 งวด)
    for i in range(10):
        counts = 0
        for row in draws[:50]:
            two_top = row.get('twoTop', '')
            if not two_top:
                continue
            if str(i) in str(two_top).zfill(2):
                counts += 1
        if 8 <= counts <= 12: 
            scores[i] += 10.0

    return scores

def main():
    print("⏳ [SP Math] เริ่มต้นวิเคราะห์สมการคณิตศาสตร์ (Multi-Market)...")
    
    # 🔍 สแกนหาไฟล์ raw_ ทั้งหมด
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    if not raw_files:
        print("❌ [SP Math] ไม่พบไฟล์ข้อมูลดิบ (raw_*.json)!")
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

            print(f"🧮 กำลังคำนวณสูตรหุ้น: {market_name.upper()}")
            
            # ส่งข้อมูลไปเข้าสมการของพี่
            math_scores = analyze_math(draws)
            
            # จัดอันดับตัวเลข
            ranked_digits = sorted([(str(i), s) for i, s in enumerate(math_scores)], key=lambda x: x[1], reverse=True)
            
            # จัดเตรียมแพ็กเกจข้อมูล (เพิ่ม field "market" เข้าไป)
            result = {
                "bot_name": "Math_Probability_V1",
                "market": market_name,
                "top_digits": [r[0] for r in ranked_digits],
                "raw_scores": math_scores,
                "status": "success"
            }
            
            # 💾 บันทึกไฟล์แยกตามชื่อหุ้น เช่น result_math_nikkei.json
            out_file = os.path.join(DATA_DIR, f"result_math_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
                
            print(f"  ✅ บันทึกผลสำเร็จ -> result_math_{market_name}.json")
            
        except Exception as e:
            print(f"❌ Error ตอนคำนวณตลาด {market_name}: {e}")

    print("🎉 [SP Math] วิเคราะห์เสร็จสิ้นครบทุกตลาด!")

if __name__ == "__main__":
    main()
