# -*- coding: utf-8 -*-
#
# stock_full_permutation.py
# ====================================================
# Full digit permutation analysis on stock lotteries.
# Uses ALL digits of opening price and ALL digits of closing price.
# Tests every position permutation to find any predictive combination.
#
# Two prediction modes:
#   SAME-DAY: today's open digits -> today's twoTop (last 2 of close)
#             (No close-digit leakage; you know open during day)
#   CROSS-DAY: yesterday's full open + full close digits -> today's twoTop
#
# For each mode, tests:
#   - All single-digit predictions (rude): 1 position -> twoTop_front or back
#     Baseline 10%, breakeven 10% (10 baht stake / 100 win)
#   - All ordered-pair predictions (exact pair): 2 positions -> twoTop pair
#     Baseline 1%, breakeven 1% (1 baht stake / 100 win)
#
# Train/test split: 70/30 (oldest 70% train, newest 30% test)
# Survival: train > breakeven AND test Wilson lower bound > breakeven.

import json
import os
import glob
import numpy as np
from math import sqrt
from itertools import product

DATA_DIR = 'data'
OUTPUT_FILE = os.path.join(DATA_DIR, 'stock_full_permutation_report.json')
TRAIN_FRAC = 0.7
N_DIGITS = 5  # use last 5 digits of open and close


def extract_digits(price_str, n=N_DIGITS):
    s = ''.join(c for c in str(price_str) if c.isdigit())
    if not s:
        return None
    s = s[-n:].zfill(n)
    return [int(c) for c in s]


def wilson_lower(wins, n, z=1.645):
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z*z/n
    center = p + z*z/(2*n)
    margin = z * sqrt((p*(1-p) + z*z/(4*n))/n)
    return max(0.0, (center - margin)/denom)


def load_market(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        draws = json.load(f)

    rows = []
    for d in draws:
        tt = str(d.get('twoTop', '')).zfill(2)
        if len(tt) != 2 or not tt.isdigit():
            continue
        front = int(tt[0])
        back = int(tt[1])
        op_digits = extract_digits(d.get('open', ''))
        if op_digits is None:
            continue
        # close = open + diff, but we just take twoTop as last 2 of close
        # for full close digits, derive: close_str = open + diff
        try:
            open_val = float(''.join(c for c in str(d.get('open', '')) if c.isdigit() or c == '.'))
            diff_val = float(d.get('diff', 0))
            close_val = open_val + diff_val
            close_str = f"{close_val:.0f}".replace('.', '')
        except Exception:
            close_str = ''
        cl_digits = extract_digits(close_str) if close_str else None
        if cl_digits is None:
            cl_digits = [-1] * N_DIGITS
        rows.append({
            'front': front,
            'back': back,
            'open_digits': op_digits,
            'close_digits': cl_digits,
        })
    return rows


def evaluate_market(market_name, rows):
    n = len(rows)
    if n < 200:
        return None

    # Reverse: chronological order (oldest first)
    rows = list(reversed(rows))

    split = int(TRAIN_FRAC * n)
    train_idx = list(range(1, split))   # need t-1 for cross-day
    test_idx = list(range(split, n))

    open_d = np.array([r['open_digits'] for r in rows])    # (n, 5)
    close_d = np.array([r['close_digits'] for r in rows])   # (n, 5)
    fronts = np.array([r['front'] for r in rows])
    backs = np.array([r['back'] for r in rows])

    findings = []

    # ============ SAME-DAY: today's open digits -> today's twoTop ============
    # 5 positions of today's open

    # Single-digit (rude): for each open position, predict twoTop_front or back
    for i in range(N_DIGITS):
        for tgt_name, tgt in [('t_front', fronts), ('t_back', backs)]:
            train_h = sum(1 for t in train_idx
                          if open_d[t, i] >= 0 and open_d[t, i] == tgt[t])
            train_n = sum(1 for t in train_idx if open_d[t, i] >= 0)
            test_h = sum(1 for t in test_idx
                         if open_d[t, i] >= 0 and open_d[t, i] == tgt[t])
            test_n = sum(1 for t in test_idx if open_d[t, i] >= 0)
            if train_n < 100 or test_n < 50:
                continue
            train_pct = train_h / train_n * 100
            test_pct = test_h / test_n * 100
            wilson = wilson_lower(test_h, test_n) * 100
            findings.append({
                'mode': 'sameday',
                'type': 'A_single',
                'strategy': f'open_pos{i}->{tgt_name}',
                'train_pct': round(train_pct, 2),
                'test_pct': round(test_pct, 2),
                'test_wilson_lower': round(wilson, 2),
                'train_n': train_n, 'test_n': test_n,
                'baseline': 10.0, 'breakeven': 10.0,
                'survives': train_pct > 11.0 and wilson > 10.0,
            })

    # Pair (exact match): (open[i], open[j]) -> (front, back)
    for i, j in product(range(N_DIGITS), repeat=2):
        if i == j:
            continue
        train_h = sum(1 for t in train_idx
                      if open_d[t, i] == fronts[t] and open_d[t, j] == backs[t])
        test_h = sum(1 for t in test_idx
                     if open_d[t, i] == fronts[t] and open_d[t, j] == backs[t])
        train_n, test_n = len(train_idx), len(test_idx)
        train_pct = train_h / train_n * 100
        test_pct = test_h / test_n * 100
        wilson = wilson_lower(test_h, test_n) * 100
        findings.append({
            'mode': 'sameday',
            'type': 'B_pair',
            'strategy': f'open_({i},{j})->pair',
            'train_pct': round(train_pct, 2),
            'test_pct': round(test_pct, 2),
            'test_wilson_lower': round(wilson, 2),
            'train_n': train_n, 'test_n': test_n,
            'baseline': 1.0, 'breakeven': 1.0,
            'survives': train_pct > 1.5 and wilson > 1.0,
        })

    # ============ CROSS-DAY: yesterday's full open + close -> today's twoTop ============
    # 10 positions total (5 from open, 5 from close) of yesterday

    # Helper: get yesterday's combined digit at virtual position
    # virtual pos 0..4 = open_d[t-1, 0..4]
    # virtual pos 5..9 = close_d[t-1, 0..4]
    def y_digit(t, vp):
        if vp < N_DIGITS:
            return open_d[t-1, vp]
        return close_d[t-1, vp - N_DIGITS]

    n_pool = 2 * N_DIGITS  # 10

    # Single-digit cross-day
    for vp in range(n_pool):
        for tgt_name, tgt in [('t_front', fronts), ('t_back', backs)]:
            train_h = sum(1 for t in train_idx
                          if y_digit(t, vp) >= 0 and y_digit(t, vp) == tgt[t])
            train_n = sum(1 for t in train_idx if y_digit(t, vp) >= 0)
            test_h = sum(1 for t in test_idx
                         if y_digit(t, vp) >= 0 and y_digit(t, vp) == tgt[t])
            test_n = sum(1 for t in test_idx if y_digit(t, vp) >= 0)
            if train_n < 100 or test_n < 50:
                continue
            label = f'y_open_{vp}' if vp < N_DIGITS else f'y_close_{vp-N_DIGITS}'
            train_pct = train_h / train_n * 100
            test_pct = test_h / test_n * 100
            wilson = wilson_lower(test_h, test_n) * 100
            findings.append({
                'mode': 'crossday',
                'type': 'A_single',
                'strategy': f'{label}->{tgt_name}',
                'train_pct': round(train_pct, 2),
                'test_pct': round(test_pct, 2),
                'test_wilson_lower': round(wilson, 2),
                'train_n': train_n, 'test_n': test_n,
                'baseline': 10.0, 'breakeven': 10.0,
                'survives': train_pct > 11.0 and wilson > 10.0,
            })

    # Pair cross-day: 10 x 9 = 90 ordered pairs
    for vi, vj in product(range(n_pool), repeat=2):
        if vi == vj:
            continue
        train_h = 0
        for t in train_idx:
            if y_digit(t, vi) >= 0 and y_digit(t, vj) >= 0:
                if y_digit(t, vi) == fronts[t] and y_digit(t, vj) == backs[t]:
                    train_h += 1
        test_h = 0
        for t in test_idx:
            if y_digit(t, vi) >= 0 and y_digit(t, vj) >= 0:
                if y_digit(t, vi) == fronts[t] and y_digit(t, vj) == backs[t]:
                    test_h += 1
        train_n, test_n = len(train_idx), len(test_idx)
        train_pct = train_h / train_n * 100
        test_pct = test_h / test_n * 100
        wilson = wilson_lower(test_h, test_n) * 100
        label_i = f'open_{vi}' if vi < N_DIGITS else f'close_{vi-N_DIGITS}'
        label_j = f'open_{vj}' if vj < N_DIGITS else f'close_{vj-N_DIGITS}'
        findings.append({
            'mode': 'crossday',
            'type': 'B_pair',
            'strategy': f'y_({label_i},{label_j})->pair',
            'train_pct': round(train_pct, 2),
            'test_pct': round(test_pct, 2),
            'test_wilson_lower': round(wilson, 2),
            'train_n': train_n, 'test_n': test_n,
            'baseline': 1.0, 'breakeven': 1.0,
            'survives': train_pct > 1.5 and wilson > 1.0,
        })

    return {
        'market': market_name, 'n_draws': n,
        'train_size': len(train_idx), 'test_size': len(test_idx),
        'n_digits_used': N_DIGITS,
        'findings': findings,
    }


def main():
    print('=' * 80)
    print('STOCK FULL DIGIT PERMUTATION ANALYSIS')
    print(f'Using last {N_DIGITS} digits of OPEN and CLOSE prices')
    print('Train/test 70/30 with Wilson 95% lower-bound on test')
    print('=' * 80)

    raw_files = sorted(glob.glob(os.path.join(DATA_DIR, 'raw_*.json')))
    all_results = []
    all_flat = []

    for fp in raw_files:
        if 'raw_excel' in fp:
            continue
        market = os.path.basename(fp).replace('raw_', '').replace('.json', '')
        rows = load_market(fp)
        result = evaluate_market(market, rows)
        if result is None:
            continue
        all_results.append(result)
        for f in result['findings']:
            f['market'] = market
            all_flat.append(f)

        survivors = [f for f in result['findings'] if f['survives']]
        n_tests_market = len(result['findings'])
        print(f"\n[{market.upper()}] n={result['n_draws']}, "
              f"tests={n_tests_market}, survivors={len(survivors)}")
        # Show top 5 by lift
        sorted_f = sorted(result['findings'],
                          key=lambda x: -(x['train_pct'] - x['baseline']))
        print(f"  TOP 5 by train lift over baseline:")
        for f in sorted_f[:5]:
            mark = ' <SURVIVE>' if f['survives'] else ''
            print(f"    {f['mode']:9s} {f['type']:8s} {f['strategy']:35s}"
                  f" train={f['train_pct']:5.2f}% test={f['test_pct']:5.2f}%"
                  f" wilson={f['test_wilson_lower']:5.2f}% (base {f['baseline']}%)"
                  f"{mark}")

    n_total = len(all_flat)
    n_survive = sum(1 for f in all_flat if f['survives'])
    bonf_alpha = 0.05 / n_total if n_total else 1
    print()
    print('=' * 80)
    print(f'GRAND TOTAL: {n_total} tests across {len(all_results)} markets')
    print(f'Bonferroni alpha (0.05 / n_total): {bonf_alpha:.6f}')
    print(f'Strategies surviving train + Wilson-lower checks: {n_survive}')
    print('=' * 80)

    if n_survive > 0:
        print('\nSURVIVING STRATEGIES (sorted by test_wilson_lower desc):')
        survivors = [f for f in all_flat if f['survives']]
        survivors.sort(key=lambda x: -x['test_wilson_lower'])
        print(f"\n{'#':>3s} {'Market':>10s} {'Mode':>9s} {'Type':>8s} {'Strategy':30s}"
              f" {'Train':>7s} {'Test':>7s} {'Wilson':>7s} {'Edge':>7s}")
        print('-' * 92)
        for i, f in enumerate(survivors, 1):
            edge = f['test_wilson_lower'] - f['breakeven']
            print(f"{i:>3d} {f['market']:>10s} {f['mode']:>9s} {f['type']:>8s} "
                  f"{f['strategy']:30s} {f['train_pct']:>6.2f}% "
                  f"{f['test_pct']:>6.2f}% {f['test_wilson_lower']:>6.2f}% "
                  f"+{edge:>5.2f}pp")
    else:
        print('\nNo strategy passed train + Wilson-lower checks.')
        print('No exploitable digit-permutation edge found.')

    # Save report
    report = {
        'description': 'Full digit permutation analysis with train/test split',
        'n_digits_per_price': N_DIGITS,
        'train_frac': TRAIN_FRAC,
        'n_total_tests': n_total,
        'n_survives': n_survive,
        'bonferroni_alpha': bonf_alpha,
        'markets': all_results,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2,
                  default=lambda o: float(o) if isinstance(o, np.floating) else str(o))
    print(f'\nFull report -> {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
