import json
import os

# ==========================================
# ⚙️ OPTIMIZER CONFIG (V2.5)
# ==========================================
OUTPUT_SETTINGS = 'market_settings.json'

# ---------------------------------------------------------
# 🟢 [ENABLE/DISABLE] กลยุทธ์ไฟเหลือง (Yellow Strategy)
# ---------------------------------------------------------
# ใส่ 0.5 = แทงครึ่งเดียว (ประหยัดทุนเมื่อบอทไม่มั่นใจ)
# ใส่ 1.0 = แทงเต็ม (บู๊ทุกสถานการณ์ยกเว้นไฟแดง)
YELLOW_BET_RATE = 0.5 
# ---------------------------------------------------------

# เลือกจำนวนเลขที่จะเล่น (2 = รูด 2 ตัวแรก / 5 = รูด 5 ตัวแรก)
TARGET_DIGITS = 2 

def main():
    # รายชื่อตลาดหุ้นทั้งหมด
    markets = ['nikkei', 'china', 'hangseng', 'taiwan', 'india', 'germany', 'uk', 'dow']
    
    settings = {}
    for m in markets:
        settings[m] = {
            'base_limit': 80,          # เกณฑ์ Chaos Index พื้นฐาน
            'min_elite': 28,           # เกณฑ์คัดกรองบอทเก่ง
            'veto_mult': 1.15,         # ค่าความต่างของการโหวต
            'target_digits': TARGET_DIGITS,
            'yellow_bet_rate': YELLOW_BET_RATE
        }
        
    with open(OUTPUT_SETTINGS, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        
    print(f"✅ บันทึกการตั้งค่าสำเร็จ!")
    print(f"🎯 เป้าหมาย: รูด {TARGET_DIGITS} ตัว")
    print(f"🟡 กลยุทธ์ไฟเหลือง: แทงสัดส่วน {YELLOW_BET_RATE}")

if __name__ == "__main__":
    main()
