import json, os, glob, numpy as np

from itertools import combinations



# =====================================================================

# ⚖️ Configuration - Risk Tuner (Multi-Dimensional P80 - 40 Units Mode)

# =====================================================================

DATA_DIR = "../data/"

OUTPUT_FILE = "../data/risk_config.json"



def calculate_p80_for_window(draws, all_pairs, window):

"""ฟังก์ชันหาค่า P80 แยกตามระยะเวลา โดยใช้ลอจิกรูดหน้า-หลังเต็มจำนวน"""

actual_window = min(window, len(draws))

if actual_window < 5: return 0


test_draws = draws[:actual_window]

win_rates = []


for pair in all_pairs:

wins = 0

for row in test_draws:

num = str(row.get('twoTop', '')).zfill(2)

if not num.isdigit(): continue


# 🔻 ลอจิกตรวจเช็คแบบเดียวกับ Money Commander (ไม่ตัดซ้ำ) 🔻

# ถ้าตัวใดตัวหนึ่งเข้าตำแหน่งหน้าหรือหลัง ก็นับว่า "ชนะ" ในงวดนั้น

has_hit = False

if str(pair[0]) == num[0] or str(pair[0]) == num[1] or \

str(pair[1]) == num[0] or str(pair[1]) == num[1]:

has_hit = True


if has_hit:

wins += 1


win_rates.append((wins / actual_window) * 100)


# คืนค่าเปอร์เซ็นไทล์ที่ 80 (เกณฑ์สำหรับคัดหัวกะทิ Top 20%)

return round(np.percentile(win_rates, 80), 2)



def main():

print("⏳ [Risk Tuner] กำลังสร้างเกณฑ์มาตรฐานหลายมิติ (กลยุทธ์ 40 ชุด)...")

raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))


# สร้างคู่เลข 0-9 จับคู่กันเองทั้งหมด (45 คู่) เพื่อใช้เป็นฐานวัดค่าเฉลี่ยตลาด

all_pairs = list(combinations(range(10), 2))


multi_market_config = {"markets": {}}


for file_path in raw_files:

if "raw_excel.json" in file_path: continue

market_name = os.path.basename(file_path).replace("raw_", "").replace(".json", "")


with open(file_path, 'r', encoding='utf-8') as f:

draws = json.load(f)

if not draws: continue


print(f" ⚖️ วิเคราะห์เกณฑ์ตลาด: {market_name.upper()}")


# 🔻 คำนวณเกณฑ์ P80 แยก 4 ระยะเพื่อให้ยุติธรรมกับบอททุกสาย 🔻

p80_15 = calculate_p80_for_window(draws, all_pairs, 15)

p80_30 = calculate_p80_for_window(draws, all_pairs, 30)

p80_60 = calculate_p80_for_window(draws, all_pairs, 60)

p80_100 = calculate_p80_for_window(draws, all_pairs, 100)


# ค่าเฉลี่ยรวมคือ Min Winrate ที่บอทต้องทำให้ได้เพื่อจะได้รับความไว้วางใจ

combined_min_winrate = round((p80_15 + p80_30 + p80_60 + p80_100) / 4, 2)


multi_market_config["markets"][market_name] = {

"p80_steps": {

"15d": p80_15,

"30d": p80_30,

"60d": p80_60,

"100d": p80_100

},

"dynamic_min_winrate": combined_min_winrate

}


print(f" -> P80 [15d: {p80_15}% | 100d: {p80_100}%] | เกณฑ์กลาง: {combined_min_winrate}%")



os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:

json.dump(multi_market_config, f, ensure_ascii=False, indent=4)


print(f"\n✅ [Risk Tuner] เซ็ตเกณฑ์มาตรฐาน Multi-Phase สำเร็จ!")



if __name__ == "__main__":

main()
