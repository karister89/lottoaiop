# -*- coding: utf-8 -*-

# “””
diagnostic_uniformity.py  (V4 - Reality Check)

รันครั้งเดียว/สัปดาห์ - ทดสอบว่าหลักหน่วยและหลักสิบของแต่ละตลาด
“สุ่มจริง” หรือไม่ ด้วย chi-square goodness-of-fit test

หาก p-value > 0.05 ทุกตลาด → digit ใกล้เคียง uniform random
→ ระบบทำนายไม่มีทางมี edge ยั่งยืน (ผลที่ดูดีคือ noise)

หาก p-value < 0.05 ตลาดบางอัน → มีความเอียงสถิติบางอย่าง
→ มีโอกาสมี edge แต่ต้องระวัง overfit
“””

import json
import os
import glob
import numpy as np

DATA_DIR = “data”
OUTPUT_FILE = os.path.join(DATA_DIR, “uniformity_report.json”)

def chi_square_uniform(observed, expected_uniform=True):
“””
Chi-square goodness-of-fit test เทียบกับ uniform distribution
คืน (chi2_stat, df, p_value_approx)

```
ใช้ scipy ไม่ได้ (จะเพิ่ม dep) - ใช้ approximation ของ p-value จากตาราง
df = 9 (10 categories - 1)
"""
obs = np.asarray(observed, dtype=float)
n = obs.sum()
if n == 0:
    return 0.0, 9, 1.0
expected = n / len(obs)
chi2 = ((obs - expected) ** 2 / expected).sum()

# p-value approximation สำหรับ df=9 (Wilson-Hilferty transformation)
# X^2 ~ chi-sq(df) → ((X^2/df)^(1/3) - (1 - 2/(9*df))) / sqrt(2/(9*df)) ~ N(0,1)
df = 9
if chi2 <= 0:
    return chi2, df, 1.0
z = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / np.sqrt(2 / (9 * df))
# p = 1 - Phi(z); ใช้ approximation ของ Phi
p = 0.5 * (1 - erf_approx(z / np.sqrt(2)))
return float(chi2), df, float(max(0, min(1, p)))
```

def erf_approx(x):
“”“Abramowitz-Stegun erf approximation”””
sign = np.sign(x)
x = abs(x)
a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
p = 0.3275911
t = 1.0 / (1.0 + p * x)
y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x * x)
return sign * y

def analyze_market(draws, market_name):
counts_f = [0] * 10
counts_b = [0] * 10

```
for row in draws:
    num_str = str(row.get('twoTop', '')).zfill(2)
    if len(num_str) != 2 or not num_str.isdigit():
        continue
    counts_f[int(num_str[0])] += 1
    counts_b[int(num_str[1])] += 1

chi2_f, df_f, p_f = chi_square_uniform(counts_f)
chi2_b, df_b, p_b = chi_square_uniform(counts_b)

n_total = sum(counts_f)
expected = n_total / 10

return {
    'market': market_name,
    'n_draws': n_total,
    'front': {
        'counts': counts_f,
        'expected_per_digit': round(expected, 1),
        'chi2': round(chi2_f, 2),
        'p_value': round(p_f, 4),
        'verdict': verdict_from_p(p_f),
    },
    'back': {
        'counts': counts_b,
        'expected_per_digit': round(expected, 1),
        'chi2': round(chi2_b, 2),
        'p_value': round(p_b, 4),
        'verdict': verdict_from_p(p_b),
    },
}
```

def verdict_from_p(p):
if p < 0.01:
return “✅ Non-uniform (strong signal possible)”
elif p < 0.05:
return “🟡 Slight non-uniformity (weak signal)”
elif p < 0.20:
return “🟠 Borderline uniform”
else:
return “🔴 Effectively uniform (no edge expected)”

def main():
print(”\n” + “=” * 75)
print(“🔬 [Uniformity Test] เช็ค digit distribution ของแต่ละตลาด”)
print(”=” * 75)

```
raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
report = {'description': 'Chi-square goodness-of-fit vs uniform U(0,9). H0: digits are uniform random.',
          'markets': {}}

overall_verdict = []
for fp in raw_files:
    if 'raw_excel' in fp:
        continue
    market = os.path.basename(fp).replace('raw_', '').replace('.json', '')
    with open(fp, 'r', encoding='utf-8') as f:
        draws = json.load(f)
    result = analyze_market(draws, market)
    report['markets'][market] = result
    print(f"\n📊 {market.upper()} ({result['n_draws']} งวด)")
    print(f"   หน้า: chi2={result['front']['chi2']}  p={result['front']['p_value']}  {result['front']['verdict']}")
    print(f"   หลัง: chi2={result['back']['chi2']}  p={result['back']['p_value']}  {result['back']['verdict']}")
    overall_verdict.append(result['front']['p_value'] < 0.05 or result['back']['p_value'] < 0.05)

n_signal = sum(overall_verdict)
n_total = len(overall_verdict)
print("\n" + "=" * 75)
if n_signal == 0:
    print(f"⚠️  ตลาดทุกตลาด digit ดูเหมือน uniform random ({n_total}/{n_total})")
    print("    → ระบบจะไม่สามารถสร้าง edge จากการกระจายตัวของเลข")
    print("    → ผลกำไรในระยะยาวคาดว่า ≈ 0 (เกมเป็น zero-EV)")
else:
    print(f"✅ ตลาดที่มีการเอียงสถิติ: {n_signal}/{n_total}")
    print("    → มีโอกาสสร้าง edge ได้ในตลาดเหล่านั้น")
    print("    → ดู report ละเอียดใน uniformity_report.json")
print("=" * 75 + "\n")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"✅ บันทึก → {OUTPUT_FILE}\n")
```

if **name** == “**main**”:
main()
