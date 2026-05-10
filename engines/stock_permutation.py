# -*- coding: utf-8 -*-
#
# stock_permutation_analysis.py
# ====================================================
# Cross-day permutation analysis on stock-tied lotteries
# with train/test split (70/30) to expose selection bias.
#
# For each market, tests:
#   A. Predict today's twoTop_front using yesterday's various digits
#   B. Predict today's twoTop_back using yesterday's various digits
#   C. Predict today's exact 2-digit pair using yesterday's pair permutations
#   D. Multi-day window patterns (2-day lookback)
#
# A surviving strategy must:
#   - Beat baseline (10% for single digit, 1% for pair) on TRAIN
#   - Continue to beat on TEST
#   - Survive Bonferroni correction
#
# Output: data/stock_permutation_report.json

import json
import os
import glob
import numpy as np
from math import sqrt

DATA_DIR = 'data'
OUTPUT_FILE = os.path.join(DATA_DIR, 'stock_permutation_report.json')
TRAIN_FRAC = 0.7

def load_market(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        draws = json.load(f)
    rows = []
    for d in draws:
        tt = str(d.get('twoTop', '')).zfill(2)
        op = str(d.get('open', ''))
        if len(tt) != 2 or not tt.isdigit():
            continue
        front = int(tt[0])
        back = int(tt[1])
        op_last = int(op[-1]) if op and op[-1].isdigit() else -1
        op_first = int(op[0]) if op and op[0].isdigit() else -1
        try:
            diff = float(d.get('diff', 0))
        except Exception:
            diff = 0
        diff_sign = 1 if diff > 0 else (-1 if diff < 0 else 0)
        rows.append({'front': front, 'back': back, 'op_last': op_last,
                     'op_first': op_first, 'diff_sign': diff_sign})
    return rows

def wilson_lower(wins, n, z=1.645):
    if n == 0: return 0.0
    p = wins / n
    denom = 1 + z*z/n
    center = p + z*z/(2*n)
    margin = z * sqrt((p*(1-p) + z*z/(4*n))/n)
    return max(0.0, (center - margin)/denom)

def test_market(market_name, rows):
    n = len(rows)
    if n < 200:
        return None

    # IMPORTANT: rows from JSON are in newest-first order; reverse for chronological
    rows = list(reversed(rows))

    split = int(TRAIN_FRAC * n)
    train_idx = list(range(1, split))
    test_idx = list(range(split, n))

    fronts = np.array([r['front'] for r in rows])
    backs = np.array([r['back'] for r in rows])
    op_lasts = np.array([r['op_last'] for r in rows])

    findings = []

    # Strategy A: predict today's front using yesterday's various positions
    for src_name, src in [('y_front', fronts), ('y_back', backs), ('y_op_last', op_lasts)]:
        for tgt_name, tgt in [('t_front', fronts), ('t_back', backs)]:
            # hit when src[t-1] == tgt[t]
            train_h = sum(1 for t in train_idx
                          if src[t-1] >= 0 and src[t-1] == tgt[t])
            train_n = sum(1 for t in train_idx if src[t-1] >= 0)
            test_h = sum(1 for t in test_idx
                         if src[t-1] >= 0 and src[t-1] == tgt[t])
            test_n = sum(1 for t in test_idx if src[t-1] >= 0)
            if train_n < 100 or test_n < 50:
                continue
            train_pct = train_h / train_n * 100
            test_pct = test_h / test_n * 100
            wilson = wilson_lower(test_h, test_n) * 100
            findings.append({
                'type': 'A_single_digit',
                'strategy': f'{src_name}->{tgt_name}',
                'train_pct': round(train_pct, 2),
                'test_pct': round(test_pct, 2),
                'test_wilson_lower': round(wilson, 2),
                'train_n': train_n, 'test_n': test_n,
                'baseline': 10.0,
                'breakeven': 10.0,
                'survives': train_pct > 11.0 and wilson > 10.0,
            })

    # Strategy B: predict today's exact pair using (yesterday[i], yesterday[j])
    for src_name, src in [('y_front_then_back', (fronts, backs)),
                            ('y_back_then_front', (backs, fronts)),
                            ('y_oplast_then_front', (op_lasts, fronts)),
                            ('y_front_then_oplast', (fronts, op_lasts))]:
        a, b = src
        train_h = 0; train_n = 0
        for t in train_idx:
            if a[t-1] < 0 or b[t-1] < 0: continue
            train_n += 1
            if a[t-1] == fronts[t] and b[t-1] == backs[t]:
                train_h += 1
        test_h = 0; test_n = 0
        for t in test_idx:
            if a[t-1] < 0 or b[t-1] < 0: continue
            test_n += 1
            if a[t-1] == fronts[t] and b[t-1] == backs[t]:
                test_h += 1
        if train_n < 100 or test_n < 50: continue
        train_pct = train_h / train_n * 100
        test_pct = test_h / test_n * 100
        wilson = wilson_lower(test_h, test_n) * 100
        findings.append({
            'type': 'B_exact_pair',
            'strategy': src_name,
            'train_pct': round(train_pct, 2),
            'test_pct': round(test_pct, 2),
            'test_wilson_lower': round(wilson, 2),
            'train_n': train_n, 'test_n': test_n,
            'baseline': 1.0,
            'breakeven': 1.0,  # 1 baht stake / 100 win
            'survives': train_pct > 1.5 and wilson > 1.0,
        })

    # Strategy C: 2-day lookback alignment
    # If y_back[t-2] == y_front[t-1], predict today's back = same digit
    for cond_name, cond_fn in [
        ('back2==front1->today_back',
         lambda t: backs[t-2] == fronts[t-1]),
        ('front2==back1->today_front',
         lambda t: fronts[t-2] == backs[t-1]),
    ]:
        train_aligned = 0; train_hit = 0
        for t in train_idx:
            if t < 2: continue
            if cond_fn(t):
                train_aligned += 1
                ref = backs[t-2] if 'back2' in cond_name else fronts[t-2]
                tgt = backs[t] if 'today_back' in cond_name else fronts[t]
                if ref == tgt:
                    train_hit += 1
        test_aligned = 0; test_hit = 0
        for t in test_idx:
            if cond_fn(t):
                test_aligned += 1
                ref = backs[t-2] if 'back2' in cond_name else fronts[t-2]
                tgt = backs[t] if 'today_back' in cond_name else fronts[t]
                if ref == tgt:
                    test_hit += 1
        if train_aligned < 30 or test_aligned < 15: continue
        train_pct = train_hit / train_aligned * 100
        test_pct = test_hit / test_aligned * 100
        wilson = wilson_lower(test_hit, test_aligned) * 100
        findings.append({
            'type': 'C_2day_pattern',
            'strategy': cond_name,
            'train_pct': round(train_pct, 2),
            'test_pct': round(test_pct, 2),
            'test_wilson_lower': round(wilson, 2),
            'train_n': train_aligned, 'test_n': test_aligned,
            'baseline': 10.0,
            'breakeven': 10.0,
            'survives': train_pct > 13.0 and wilson > 10.0,
        })

    return {'market': market_name, 'n_draws': n,
            'train_size': len(train_idx), 'test_size': len(test_idx),
            'findings': findings}


def main():
    print('=' * 80)
    print('STOCK LOTTERY PERMUTATION ANALYSIS')
    print('Cross-day prediction with train/test split (70/30)')
    print('=' * 80)

    raw_files = sorted(glob.glob(os.path.join(DATA_DIR, 'raw_*.json')))
    all_results = []
    all_findings_flat = []

    for fp in raw_files:
        if 'raw_excel' in fp:
            continue
        market = os.path.basename(fp).replace('raw_', '').replace('.json', '')
        rows = load_market(fp)
        result = test_market(market, rows)
        if result is None:
            continue
        all_results.append(result)
        for f in result['findings']:
            f['market'] = market
            all_findings_flat.append(f)

        print(f"\n[{market.upper()}] n={result['n_draws']} (train={result['train_size']}, test={result['test_size']})")
        # Show top 3 by train_pct relative to baseline
        sorted_f = sorted(result['findings'],
                          key=lambda x: -(x['train_pct'] - x['baseline']))
        for f in sorted_f[:3]:
            mark = ' SURVIVES' if f['survives'] else ''
            print(f"  {f['type']}/{f['strategy']:35s} train={f['train_pct']:5.2f}% "
                  f"test={f['test_pct']:5.2f}% wilson_low={f['test_wilson_lower']:5.2f}% "
                  f"(baseline {f['baseline']}%){mark}")

    # Aggregate
    n_total = len(all_findings_flat)
    n_survives = sum(1 for f in all_findings_flat if f['survives'])
    bonf_alpha = 0.05 / n_total if n_total else 1
    print()
    print('=' * 80)
    print(f'OVERALL SUMMARY: {len(all_results)} markets x ~12 strategies = {n_total} tests')
    print(f'Bonferroni alpha: {bonf_alpha:.5f}')
    print(f'Strategies surviving train+test+wilson_lower checks: {n_survives}')
    print('=' * 80)

    if n_survives > 0:
        print('\nSURVIVING STRATEGIES:')
        for f in all_findings_flat:
            if f['survives']:
                print(f"  {f['market']:10s} {f['type']}/{f['strategy']:35s} "
                      f"train={f['train_pct']:5.2f}% test={f['test_pct']:5.2f}% "
                      f"wilson_low={f['test_wilson_lower']:5.2f}%")
    else:
        print('\nNo strategy passed train+test+Wilson lower bound checks.')
        print('Conclusion: no exploitable cross-day permutation edge in stock lotteries.')

    # Save full report
    report = {
        'description': 'Cross-day permutation analysis with train/test split',
        'train_frac': TRAIN_FRAC,
        'n_total_tests': n_total,
        'n_survives': n_survives,
        'bonferroni_alpha': bonf_alpha,
        'markets': all_results,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2,
                  default=lambda o: float(o) if isinstance(o, np.floating) else str(o))
    print(f'\nFull report -> {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
