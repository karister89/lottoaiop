import json
import os
import glob
import pandas as pd

# =====================================================================
# ⚙️ Configuration - SP AI (Multi-Market Edition)
# =====================================================================
DATA_DIR = "../data/"

def analyze_pattern(draws):
    """
    🔻 สมการออริจินัล: AI Pattern Matching (Distance Weighting) 🔻
    """
    scores = [0.0] * 10
    df = pd.DataFrame(draws)
    
    # 🛑 ดักกระแทก: ถ้ามีข้อมูลน้อยกว่า 2 งวด จะไม่สามารถเทียบแพทเทิร์นอดีตได้
    if df.empty or len(df) < 2:
        return scores
        
    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    current_diff = df.iloc[0]['diff']
    
    # คำนวณหาระยะห่าง (ความคล้ายคลึง) แล้วดึง 30 อันดับที่คล้ายวันนี้ที่สุด
    df['distance'] = abs(df['diff'] - current_diff)
    similar_past = df.iloc[1:].sort_values(by='distance').head(30)
    
    for index, row in similar_past.iterrows():
        # ดักจับกรณีค่าว่าง
        two_top = row.get('twoTop', '')
        if pd.isna(two_top) or not two_top:
            continue
            
        num_str = str(two_top).zfill(2)
        
        if len(num_str) == 2 and num_str.isdigit():
            # ยิ่งระยะห่างน้อย (คล้ายมาก) น้ำหนักตัวคูณยิ่งสูง
            weight = 1.0 / (row['distance'] + 0.1) 
            scores[int(num_str[0])] += weight
            scores[int(num_str[1])] += weight

    return scores

def main():
    print("⏳ [SP AI] เริ่มต้นวิเคราะห์แพทเทิร์นขั้นสูง (Multi-Market)...")
    
    # 🔍 สแกนหาไฟล์ raw_ ทั้งหมด
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    if not raw_files:
        print("❌ [SP AI] ไม่พบไฟล์ข้อมูลดิบ (raw_*.json)!")
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

            print(f"🤖 กำลังค้นหาแพทเทิร์นหุ้น: {market_name.upper()}")
            
            # ส่งข้อมูลไปเข้าสมการ AI
            ai_scores = analyze_pattern(draws)
            
            # จัดอันดับตัวเลข
            ranked_digits = sorted([(str(i), s) for i, s in enumerate(ai_scores)], key=lambda x: x[1], reverse=True)
            
            # จัดเตรียมแพ็กเกจข้อมูล (เพิ่ม field "market" เข้าไป)
            result = {
                "bot_name": "AI_Pattern_V1",
                "market": market_name,
                "top_digits": [r[0] for r in ranked_digits],
                "raw_scores": ai_scores,
                "status": "success"
            }
            
            # 💾 บันทึกไฟล์แยกตามชื่อหุ้น เช่น result_ai_nikkei.json
            out_file = os.path.join(DATA_DIR, f"result_ai_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
                
            print(f"  ✅ บันทึกผลสำเร็จ -> result_ai_{market_name}.json")
            
        except Exception as e:
            print(f"❌ Error ตอนคำนวณตลาด {market_name}: {e}")

    print("🎉 [SP AI] วิเคราะห์แพทเทิร์นเสร็จสิ้นครบทุกตลาด!")

if __name__ == "__main__":
    main()
