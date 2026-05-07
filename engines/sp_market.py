import json
import os
import glob
import pandas as pd

# =====================================================================
# ⚙️ Configuration - SP Market (Multi-Market Edition)
# =====================================================================
DATA_DIR = "../data/"

def analyze_market(draws):
    """
    🔻 สมการออริจินัลของพี่นพพล (ไม่ดัดแปลง) 🔻
    """
    scores = [0.0] * 10
    df = pd.DataFrame(draws)
    
    # กันกระแทก: ถ้าไม่มีข้อมูลให้คืนค่าคะแนน 0 กลับไป
    if df.empty: 
        return scores

    df['diff'] = pd.to_numeric(df['diff'], errors='coerce').fillna(0)
    current_diff = df.iloc[0]['diff'] 
    
    if current_diff > 0:
        past_matches = df[df['diff'] > 0].head(100)
    else:
        past_matches = df[df['diff'] <= 0].head(100)

    for _, row in past_matches.iterrows():
        # เติม .get() และเช็คความยาวนิดหน่อยเพื่อกัน Error กรณีมีแถวว่างแทรก
        num_str = str(row.get('twoTop', '')).zfill(2)
        if len(num_str) == 2 and num_str.isdigit():
            scores[int(num_str[0])] += 1.0 
            scores[int(num_str[1])] += 1.0 

    current_open_last_digit = str(df.iloc[0]['open'])[-1]
    if current_open_last_digit.isdigit():
        scores[int(current_open_last_digit)] += 1.5 

    return scores

def main():
    print("⏳ [SP Market] เริ่มต้นวิเคราะห์แนวโน้มตลาด (Multi-Market)...")
    
    # 🔍 สแกนหาไฟล์ raw_ ทั้งหมด
    raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
    
    if not raw_files:
        print("❌ [SP Market] ไม่พบไฟล์ข้อมูลดิบ (raw_*.json)!")
        return

    # 🔄 วนลูปอ่านข้อมูลทีละหุ้น
    for file_path in raw_files:
        
        # 🛑 ดักจับไฟล์ขยะ! ถ้าเจอชื่อ raw_excel.json ให้กระโดดข้ามไปเลย
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

            print(f"🔍 กำลังคำนวณสูตรหุ้น: {market_name.upper()}")
            
            # ส่งข้อมูลไปเข้าสมการของพี่
            market_scores = analyze_market(draws)
            
            # จัดอันดับตัวเลข
            ranked_digits = sorted([(str(i), s) for i, s in enumerate(market_scores)], key=lambda x: x[1], reverse=True)
            
            # จัดเตรียมแพ็กเกจข้อมูล (เพิ่ม field "market" เข้าไปด้วย)
            result = {
                "bot_name": "Market_Whale_V1",
                "market": market_name,
                "top_digits": [r[0] for r in ranked_digits],
                "raw_scores": market_scores,
                "status": "success"
            }
            
            # 💾 บันทึกไฟล์แยกตามชื่อหุ้น เช่น result_market_nikkei.json
            out_file = os.path.join(DATA_DIR, f"result_market_{market_name}.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
                
            print(f"  ✅ บันทึกผลสำเร็จ -> {out_file}")
            
        except Exception as e:
            print(f"❌ Error ตอนคำนวณตลาด {market_name}: {e}")

    print("🎉 [SP Market] วิเคราะห์เสร็จสิ้นครบทุกตลาด!")

if __name__ == "__main__":
    main()
