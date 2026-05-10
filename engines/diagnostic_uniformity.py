# -*- coding: utf-8 -*-

# “””
diagnostic_uniformity.py  (V4 - Reality Check)

Run once / weekly to test whether the front and back digits
of each market are truly random using chi-square goodness-of-fit.

If p-value > 0.05 for all markets, digits look uniform random
and the system cannot create a sustainable edge.

If some markets have p-value < 0.05, there is statistical bias
and edge is potentially achievable in those markets.
“””

import json
import os
import glob
import numpy as np

DATA_DIR = “data”
OUTPUT_FILE = os.path.join(DATA_DIR, “uniformity_report.json”)

def erf_approx(x):
“”“Abramowitz-Stegun erf approximation (no scipy dependency).”””
sign = np.sign(x)
x = abs(x)
a1 = 0.254829592
a2 = -0.284496736
a3 = 1.421413741
a4 = -1.453152027
a5 = 1.061405429
p = 0.3275911
t = 1.0 / (1.0 + p * x)
y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x * x)
return sign * y

def chi_square_uniform(observed):
“””
Chi-square goodness-of-fit vs uniform distribution over 10 categories.
Returns (chi2_stat, df, approx_p_value).
Uses Wilson-Hilferty transformation for p-value approximation (df=9).
“””
obs = np.asarray(observed, dtype=float)
n = obs.sum()
if n == 0:
return 0.0, 9, 1.0
expected = n / len(obs)
chi2 = float(((obs - expected) ** 2 / expected).sum())
df = 9
if chi2 <= 0:
return chi2, df, 1.0
z = ((chi2 / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / np.sqrt(2.0 / (9.0 * df))
p = 0.5 * (1.0 - erf_approx(z / np.sqrt(2.0)))
p = float(max(0.0, min(1.0, p)))
return chi2, df, p

def verdict_from_p(p):
if p < 0.01:
return “Non-uniform (strong signal possible)”
elif p < 0.05:
return “Slight non-uniformity (weak signal)”
elif p < 0.20:
return “Borderline uniform”
else:
return “Effectively uniform (no edge expected)”

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
expected_per = n_total / 10.0 if n_total > 0 else 0

return {
    'market': market_name,
    'n_draws': n_total,
    'front': {
        'counts': counts_f,
        'expected_per_digit': round(expected_per, 1),
        'chi2': round(chi2_f, 2),
        'p_value': round(p_f, 4),
        'verdict': verdict_from_p(p_f),
    },
    'back': {
        'counts': counts_b,
        'expected_per_digit': round(expected_per, 1),
        'chi2': round(chi2_b, 2),
        'p_value': round(p_b, 4),
        'verdict': verdict_from_p(p_b),
    },
}
```

def main():
print(”=” * 70)
print(”[Uniformity Test] Chi-square goodness-of-fit per market”)
print(”=” * 70)

```
raw_files = glob.glob(os.path.join(DATA_DIR, "raw_*.json"))
report = {
    'description': 'Chi-square goodness-of-fit vs uniform U(0,9). H0: digits are uniform random.',
    'markets': {}
}

n_signal = 0
n_total = 0
for fp in raw_files:
    if 'raw_excel' in fp:
        continue
    market = os.path.basename(fp).replace('raw_', '').replace('.json', '')
    with open(fp, 'r', encoding='utf-8') as f:
        draws = json.load(f)
    result = analyze_market(draws, market)
    report['markets'][market] = result

    print("")
    print("[" + market.upper() + "] " + str(result['n_draws']) + " draws")
    print("  Front: chi2=" + str(result['front']['chi2'])
          + "  p=" + str(result['front']['p_value'])
          + "  -> " + result['front']['verdict'])
    print("  Back:  chi2=" + str(result['back']['chi2'])
          + "  p=" + str(result['back']['p_value'])
          + "  -> " + result['back']['verdict'])

    n_total += 1
    if result['front']['p_value'] < 0.05 or result['back']['p_value'] < 0.05:
        n_signal += 1

print("")
print("=" * 70)
if n_signal == 0:
    print("All markets appear uniform random (" + str(n_total) + "/" + str(n_total) + ").")
    print("System cannot generate sustainable edge from digit distribution.")
    print("Long-run profit expectation ~= 0 (game is zero-EV).")
else:
    print("Markets with statistical bias: " + str(n_signal) + "/" + str(n_total))
    print("Edge potentially achievable in those markets.")
    print("See uniformity_report.json for details.")
print("=" * 70)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("")
print("Saved -> " + OUTPUT_FILE)
```

if **name** == “**main**”:
main()
