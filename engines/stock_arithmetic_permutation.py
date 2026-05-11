# -*- coding: utf-8 -*-
#
# stock_arithmetic_permutation.py (v4)
# ====================================================
# Tests arithmetic combinations of digits as predictors of twoTop.
#
# Predictors built from ALL digits of open and close prices.
# Target: twoTop (the actual house value used).
#
# Strategy types tested for each market:
#   A_single:   one digit -> t_front or t_back (baseline 10%)
#   B_concat:   (d_i, d_j) concatenated -> twoTop pair (baseline 1%)
#   C_sum10:    (d_i + d_j) mod 10 -> t_front or t_back
#   C_diff10:   (d_i - d_j) mod 10 -> t_front or t_back
#   C_prod10:   (d_i * d_j) mod 10 -> t_front or t_back
#   C_3sum10:   (d_i + d_j + d_k) mod 10 -> t_front or t_back
#   C_const10:  (d_i + c) mod 10 -> t_front or t_back, for c in 0..9
#   D_sum100:   (d_i + d_j) mod 100 (uses d_i*10+d_j as base) -> twoTop pair
#
# Modes:
#   sameday  : digits from today's open
#   crossday : digits from yesterday's open + yesterday's close
#
# Survives = train above breakeven by margin AND Wilson lower bound > breakeven.

import json
import os
import glob
import numpy as np
from math import sqrt
from itertools import combinations, product
from collections import Counter

DATA_DIR = 'data'
OUTPUT_FILE = os.path.join(DATA_DIR, 'stock_arithmetic_report.json')
TRAIN_FRAC = 0.7


def extract_all_digits(price_str):
    s = ''.join(c for c in str(price_str) if c.isdigit())
    if not s:
        return None
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
    lo, lc = [], []
    for d in draws:
        tt = str(d.get('twoTop', '')).zfill(2)
        if len(tt) != 2 or not tt.isdigit():
            continue
        front = int(tt[0])
        back = int(tt[1])
        op_str = str(d.get('open', ''))
        op_digits = extract_all_digits(op_str)
        if op_digits is None or len(op_digits) < 3:
            continue
        try:
            ov = float(''.join(c for c in op_str if c.isdigit() or c == '.'))
            dv = float(d.get('diff', 0))
            cv = ov + dv
            close_str = f"{cv:.2f}"
        except Exception:
            close_str = ''
        cl_digits = extract_all_digits(close_str)
        if cl_digits is None or len(cl_digits) < 3:
            continue
        lo.append(len(op_digits))
        lc.append(len(cl_digits))
        rows.append({'front': front, 'back': back,
                      'open_digits': op_digits,
                      'close_digits': cl_digits})
    if not rows:
        return [], 0, 0
    no = Counter(lo).most_common(1)[0][0]
    nc = Counter(lc).most_common(1)[0][0]
    filt = [r for r in rows if len(r['open_digits']) == no
                              and len(r['close_digits']) == nc]
    return filt, no, nc


def evaluate_market(market, rows, n_open, n_close):
    n = len(rows)
    if n < 200:
        return None
    rows = list(reversed(rows))
    split = int(TRAIN_FRAC * n)
    train_idx = list(range(1, split))
    test_idx = list(range(split, n))

    open_d = np.array([r['open_digits'] for r in rows])
    close_d = np.array([r['close_digits'] for r in rows])
    fronts = np.array([r['front'] for r in rows])
    backs = np.array([r['back'] for r in rows])

    findings = []
    train_n = len(train_idx)
    test_n = len(test_idx)

    def add_single(mode_label, formula_func, strategy_label):
        """formula_func(t) -> predicted single digit"""
        for tgt_name, tgt in [('t_front', fronts), ('t_back', backs)]:
            tr_h = sum(1 for t in train_idx if formula_func(t) == tgt[t])
            te_h = sum(1 for t in test_idx if formula_func(t) == tgt[t])
            tr_pct = tr_h / train_n * 100
            te_pct = te_h / test_n * 100
            wl = wilson_lower(te_h, test_n) * 100
            findings.append({
                'mode': mode_label,
                'type': strategy_label.split('_')[0],
                'strategy': f'{strategy_label}->{tgt_name}',
                'train_pct': round(tr_pct, 2),
                'test_pct': round(te_pct, 2),
                'test_wilson_lower': round(wl, 2),
                'train_n': train_n, 'test_n': test_n,
                'baseline': 10.0, 'breakeven': 10.0,
                'survives': tr_pct > 11.0 and wl > 10.0,
            })

    def add_pair(mode_label, formula_func, strategy_label):
        """formula_func(t) -> (front_pred, back_pred)"""
        tr_h = 0
        te_h = 0
        for t in train_idx:
            f, b = formula_func(t)
            if f == fronts[t] and b == backs[t]:
                tr_h += 1
        for t in test_idx:
            f, b = formula_func(t)
            if f == fronts[t] and b == backs[t]:
                te_h += 1
        tr_pct = tr_h / train_n * 100
        te_pct = te_h / test_n * 100
        wl = wilson_lower(te_h, test_n) * 100
        findings.append({
            'mode': mode_label,
            'type': strategy_label.split('_')[0],
            'strategy': strategy_label,
            'train_pct': round(tr_pct, 2),
            'test_pct': round(te_pct, 2),
            'test_wilson_lower': round(wl, 2),
            'train_n': train_n, 'test_n': test_n,
            'baseline': 1.0, 'breakeven': 1.0,
            'survives': tr_pct > 1.5 and wl > 1.0,
        })

    # =========================
    # SAME-DAY: today's open
    # =========================
    def od(t, i):  # open digit today
        return open_d[t, i]

    # A_single: each digit alone
    for i in range(n_open):
        add_single('sameday',
                    lambda t, i=i: od(t, i),
                    f'A_open{i}')

    # B_concat: pair of digits as twoTop guess
    for i, j in product(range(n_open), repeat=2):
        if i == j: continue
        add_pair('sameday',
                  lambda t, i=i, j=j: (od(t, i), od(t, j)),
                  f'B_concat_open({i},{j})')

    # C_sum10: (d_i + d_j) mod 10
    for i, j in combinations(range(n_open), 2):
        add_single('sameday',
                    lambda t, i=i, j=j: (od(t, i) + od(t, j)) % 10,
                    f'C_sum10_open({i},{j})')

    # C_diff10: (d_i - d_j) mod 10
    for i, j in product(range(n_open), repeat=2):
        if i == j: continue
        add_single('sameday',
                    lambda t, i=i, j=j: (od(t, i) - od(t, j)) % 10,
                    f'C_diff10_open({i},{j})')

    # C_prod10: (d_i * d_j) mod 10
    for i, j in combinations(range(n_open), 2):
        add_single('sameday',
                    lambda t, i=i, j=j: (od(t, i) * od(t, j)) % 10,
                    f'C_prod10_open({i},{j})')

    # C_3sum10: (d_i + d_j + d_k) mod 10
    for i, j, k in combinations(range(n_open), 3):
        add_single('sameday',
                    lambda t, i=i, j=j, k=k: (od(t, i) + od(t, j) + od(t, k)) % 10,
                    f'C_3sum10_open({i},{j},{k})')

    # C_const10: (d_i + c) mod 10 for c in 0..9
    for i in range(n_open):
        for c in range(10):
            add_single('sameday',
                        lambda t, i=i, c=c: (od(t, i) + c) % 10,
                        f'C_const10_open{i}+{c}')

    # D_sum100: (d_i*10 + d_j) compared to twoTop directly
    # (this is same as B_concat, skip duplicate)

    # =========================
    # CROSS-DAY: yesterday's open + close pool
    # =========================
    pool = n_open + n_close

    def yd(t, vp):
        if vp < n_open:
            return open_d[t-1, vp]
        return close_d[t-1, vp - n_open]

    def vlabel(vp):
        if vp < n_open:
            return f'yopen{vp}'
        return f'yclose{vp - n_open}'

    # A_single
    for vp in range(pool):
        add_single('crossday',
                    lambda t, vp=vp: yd(t, vp),
                    f'A_{vlabel(vp)}')

    # B_concat
    for vi, vj in product(range(pool), repeat=2):
        if vi == vj: continue
        add_pair('crossday',
                  lambda t, vi=vi, vj=vj: (yd(t, vi), yd(t, vj)),
                  f'B_concat_y({vlabel(vi)},{vlabel(vj)})')

    # C_sum10
    for vi, vj in combinations(range(pool), 2):
        add_single('crossday',
                    lambda t, vi=vi, vj=vj: (yd(t, vi) + yd(t, vj)) % 10,
                    f'C_sum10_y({vlabel(vi)},{vlabel(vj)})')

    # C_diff10
    for vi, vj in product(range(pool), repeat=2):
        if vi == vj: continue
        add_single('crossday',
                    lambda t, vi=vi, vj=vj: (yd(t, vi) - yd(t, vj)) % 10,
                    f'C_diff10_y({vlabel(vi)},{vlabel(vj)})')

    # C_prod10
    for vi, vj in combinations(range(pool), 2):
        add_single('crossday',
                    lambda t, vi=vi, vj=vj: (yd(t, vi) * yd(t, vj)) % 10,
                    f'C_prod10_y({vlabel(vi)},{vlabel(vj)})')

    # C_3sum10  (limit to avoid explosion if pool too big)
    if pool <= 16:
        for vi, vj, vk in combinations(range(pool), 3):
            add_single('crossday',
                        lambda t, vi=vi, vj=vj, vk=vk:
                            (yd(t, vi) + yd(t, vj) + yd(t, vk)) % 10,
                        f'C_3sum10_y({vlabel(vi)},{vlabel(vj)},{vlabel(vk)})')

    # C_const10
    for vp in range(pool):
        for c in range(10):
            add_single('crossday',
                        lambda t, vp=vp, c=c: (yd(t, vp) + c) % 10,
                        f'C_const10_y{vlabel(vp)}+{c}')

    return {
        'market': market, 'n_draws': n,
        'train_size': train_n, 'test_size': test_n,
        'n_open_digits': n_open, 'n_close_digits': n_close,
        'findings': findings,
    }


def main():
    print('=' * 82)
    print('STOCK ARITHMETIC PERMUTATION ANALYSIS (v4)')
    print('Tests: single, concat-pair, sum/diff/prod mod 10, 3-sum mod 10, digit+constant')
    print('=' * 82)

    raw_files = sorted(glob.glob(os.path.join(DATA_DIR, 'raw_*.json')))
    all_results = []
    all_flat = []

    for fp in raw_files:
        if 'raw_excel' in fp:
            continue
        market = os.path.basename(fp).replace('raw_', '').replace('.json', '')
        rows, no, nc = load_market(fp)
        result = evaluate_market(market, rows, no, nc)
        if result is None:
            continue
        all_results.append(result)
        for f in result['findings']:
            f['market'] = market
            all_flat.append(f)

        survs = [f for f in result['findings'] if f['survives']]
        print(f"\n[{market.upper()}] n={result['n_draws']}, "
              f"open_d={no}, close_d={nc}, "
              f"tests={len(result['findings'])}, survives={len(survs)}")
        # Show top 3 survivors
        survs.sort(key=lambda x: -x['test_wilson_lower'])
        for f in survs[:3]:
            print(f"  SURVIVE: {f['mode']:9s} {f['strategy']:50s} "
                  f"train={f['train_pct']:5.2f}% test={f['test_pct']:5.2f}% "
                  f"wilson={f['test_wilson_lower']:5.2f}%")

    n_total = len(all_flat)
    n_surv = sum(1 for f in all_flat if f['survives'])
    bonf = 0.05 / n_total if n_total else 1
    print()
    print('=' * 82)
    print(f'GRAND TOTAL: {n_total} tests across {len(all_results)} markets')
    print(f'Bonferroni alpha: {bonf:.7f}')
    print(f'Survivors (train+Wilson check, NOT Bonferroni): {n_surv}')
    print(f'Expected by chance ~5%: {n_total * 0.05:.0f}')
    print('=' * 82)

    if n_surv > 0:
        survs = [f for f in all_flat if f['survives']]
        survs.sort(key=lambda x: -x['test_wilson_lower'])
        print('\nTOP 30 SURVIVING STRATEGIES (by Wilson lower):')
        print(f"\n{'#':>3s} {'Market':>10s} {'Mode':>9s} {'Strategy':50s} "
              f"{'Train':>7s} {'Test':>7s} {'Wilson':>7s} {'Edge':>7s}")
        print('-' * 112)
        for i, f in enumerate(survs[:30], 1):
            edge = f['test_wilson_lower'] - f['breakeven']
            print(f"{i:>3d} {f['market']:>10s} {f['mode']:>9s} {f['strategy']:50s} "
                  f"{f['train_pct']:>6.2f}% {f['test_pct']:>6.2f}% "
                  f"{f['test_wilson_lower']:>6.2f}% +{edge:>5.2f}pp")

    # save
    report = {
        'description': 'Arithmetic permutation analysis (v4): sum/diff/prod/3sum/const mod 10',
        'train_frac': TRAIN_FRAC,
        'n_total_tests': n_total,
        'n_survives': n_surv,
        'bonferroni_alpha': bonf,
        'markets': all_results,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2,
                  default=lambda o: float(o) if isinstance(o, np.floating) else str(o))
    print(f'\nReport: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
