import json
import os
import glob

# =====================================================================
# ⚙️ Configuration - SP Math (V3 - Split Position)
# =====================================================================
DATA_DIR = "../data/"

def analyze_math_split(draws):
    """
    🔻 สมการออริจินัล: Gap Analysis & Sweet Spot (แยกหน้า-หลัง) 🔻
    """
    # แยกคะแนนและสถานะ หน้า(f) - หลัง(b)
    scores_f = [0.0] * 10
    scores_b = [0.0] * 10
    
    last_seen_f = {i: 0 for i in range(10)}
    last_seen_b = {i: 0 for i in range(10)}
    found_f = {i: False for i in range(10)}
    found_b = {i: False for i in range(10)}
    
    # 1. หาระยะห่าง (Gap) แยกตามตำแหน่ง
    for gap, row in enumerate(draws):
        two_top = row.get('twoTop', '')
        if not two_top: continue
            
        num_str = str(two_top).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
            ten, unit = int(num_str[0]), int(num_str[1])
            
            # เช็ค Gap หลักสิบ (หน้า)
            if not found_f[ten]:
                last_seen_f[ten] = gap
                found_f[ten] = True
            
            # เช็ค Gap หลักหน่วย (หลัง)
            if not found_b[unit]:
                last_seen_b[unit] = gap
                found_b[unit] = True
                
        if all(found_f.values()) and all(found_b.values()): 
            break

    # ให้คะแนนตามความยาวของ Gap (ยิ่งอั้นนาน คะแนนยิ่งสะสม)
    for i in range(10):
        scores_f[i] += last_seen_f[i] * 0.5
        scores_b[i] += last_seen_b[i] * 0.5

    # 2. หาความถี่จุดสมดุล (Sweet Spot) แยกตำแหน่ง
    # เกณฑ์: ใน 50 งวด ถ้าเลขไหนมาในตำแหน่งนั้น 4-6 ครั้ง (ค่าเฉลี่ยคือ 5) จะได้คะแนนพิเศษ
    for i in range(10):
        count_f = 0
        count_b = 0
        for row in draws[:50]:
            num_str = str(row.get('twoTop', '')).zfill(2)
            if not num_str.isdigit(): continue
            
            if int(num_str[0]) == i: count_f += 1
            if int(num_str[1]) == i: count_b += 1
            
        # ถ้าความถี่ตำแหน่งนั้นๆ อยู่ในจุดสมบูรณ์ (ประมาณ 10% ของงวดทั้งหมด)
        if 4 <= count_f <= 7: scores_f[i] += 10.0
        if 4 <= count_b <= 7: scores_b[i] += 10.0

    return scores_f, scores_b

def main():
    print("⏳ [SP Math] วิเคราะห์สมการคณิตศาสตร์แยกตำแหน่ง (Front-Back)...")
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    for file_path in raw_files:
        if "raw_excel.json" in file_path: continue
        market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                draws = json.load(f)
            if not draws: continue

            print(f"🧮 คำนวณ Sweet Spot หุ้น: {market_name.upper()}")
            
            # 🎯 คำนวณแยกคะแนน หน้า-หลัง
            sc_f, sc_b = analyze_math_split(draws)
            
            # จัดอันดับท็อป 5 ของแต่ละตำแหน่ง
            top_f = sorted(range(10), key=lambda i: sc_f[i], reverse=True)
            top_b = sorted(range(10), key=lambda i: sc_b[i], reverse=True)
            
            result = {
                "bot_name": "Math_Probability_V3",
                "market": market_name,
                "front_scores": sc_f,
                "back_scores": sc_b,
                "top_front": top_f[:5],
                "top_back": top_b[:5],
                "status": "success"
            }
            
            out_file = os.path.join(DATA_DIR, f"result_math_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)
                
            print(f"  ✅ บันทึกสำเร็จ -> result_math_{market_name}.json")
            
        except Exception as e:
            print(f"❌ Error {market_name}: {e}")

    print("🎉 [SP Math] วิเคราะห์เสร็จสิ้นครบทุกตลาด!")

if __name__ == "__main__":
    main()
