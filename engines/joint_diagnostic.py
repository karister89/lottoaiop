# -*- coding: utf-8 -*-
#
# joint_diagnostic.py - Comprehensive Signal Search v2
# ====================================================
# Battery of statistical tests with Bonferroni correction.
#
# Tests run per market:
#   T1: Joint (front, back) uniformity     - 100 cells chi-square
#   T2: Markov 1st-order on front          - independence test
#   T3: Markov 1st-order on back           - independence test
#   T4: Open last digit -> close back      - independence test
#   T5: Diff sign -> back digit            - independence test
#   T6: Diff quintile -> back digit        - independence test
#   T7: Sum (front+back) mod 10 uniform    - chi-square
#   T8: Back autocorr at lag 2, 3, 5, 7    - independence tests
#   T9: Cross-lag back[i] | front[i-1]     - independence (NEW)
#   T10: Cross-lag front[i] | back[i-1]    - independence (NEW)
#
# Cross-market:
#   T11: Same-day back correlation pairs

import json
import os
import glob
import numpy as np
from itertools import combinations

DATA_DIR = 'data'
OUTPUT_FILE = os.path.join(DATA_DIR, 'joint_diagnostic_report.json')

ALPHA = 0.05


def erf_approx(x):
    sign = np.sign(x)
    x = abs(x)
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x * x)
    return sign * y


def chi_sq_p(chi2, df):
    if chi2 <= 0 or df <= 0:
        return 1.0
    z = ((chi2 / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / np.sqrt(2.0 / (9.0 * df))
    p = 0.5 * (1.0 - erf_approx(z / np.sqrt(2.0)))
    return float(max(0.0, min(1.0, p)))


def chi_sq_uniform_test(observed):
    obs = np.asarray(observed, dtype=float).flatten()
    n = obs.sum()
    if n == 0:
        return 0.0, 0, 1.0, (None, 0, 0)
    expected = n / len(obs)
    chi2 = float(((obs - expected) ** 2 / expected).sum())
    df = len(obs) - 1
    p = chi_sq_p(chi2, df)
    max_idx = int(np.argmax(obs))
    return chi2, df, p, (max_idx, float(obs[max_idx]), expected)


def chi_sq_indep_test(table):
    t = np.asarray(table, dtype=float)
    n = t.sum()
    if n == 0:
        return 0.0, 0, 1.0, 0.0
    row_sums = t.sum(axis=1, keepdims=True)
    col_sums = t.sum(axis=0, keepdims=True)
    expected = (row_sums @ col_sums) / n
    mask = expected > 0
    chi2 = float((((t[mask] - expected[mask]) ** 2) / expected[mask]).sum())
    df = (t.shape[0] - 1) * (t.shape[1] - 1)
    p = chi_sq_p(chi2, df)
    k = min(t.shape) - 1
    v = float(np.sqrt(chi2 / (n * k))) if k > 0 and n > 0 else 0.0
    return chi2, df, p, v


def best_conditional_cell(table):
    t = np.asarray(table, dtype=float)
    n = t.sum()
    if n == 0:
        return None
    row_sums = t.sum(axis=1, keepdims=True)
    col_sums = t.sum(axis=0, keepdims=True)
    expected = (row_sums @ col_sums) / n
    valid = expected >= 5
    if not valid.any():
        return None
    excess = (t - expected) / np.where(expected > 0, expected, 1)
    excess[~valid] = -np.inf
    idx = np.unravel_index(np.argmax(excess), excess.shape)
    row_total = float(row_sums[idx[0], 0])
    cond_prob = float(t[idx]) / row_total if row_total > 0 else 0
    return {
        'row': int(idx[0]),
        'col': int(idx[1]),
        'observed': int(t[idx]),
        'expected': round(float(expected[idx]), 2),
        'lift_pct': round(float(excess[idx]) * 100, 2),
        'conditional_prob_pct': round(cond_prob * 100, 2),
    }


def parse_draws(draws):
    fronts, backs, diffs, opens = [], [], [], []
    for row in draws:
        num_str = str(row.get('twoTop', '')).zfill(2)
        if len(num_str) != 2 or not num_str.isdigit():
            continue
        fronts.append(int(num_str[0]))
        backs.append(int(num_str[1]))
        try:
            diffs.append(float(row.get('diff', 0)))
        except Exception:
            diffs.append(0.0)
        op = str(row.get('open', ''))
        opens.append(int(op[-1]) if op and op[-1].isdigit() else -1)
    return (np.array(fronts), np.array(backs),
            np.array(diffs), np.array(opens))


def run_market_battery(market, fronts, backs, diffs, opens):
    findings = []
    n = len(fronts)
    if n < 200:
        return findings

    # T1: Joint (front, back) uniformity
    joint = np.zeros((10, 10))
    for f, b in zip(fronts, backs):
        joint[f, b] += 1
    chi2, df, p, (mi, mc, exp) = chi_sq_uniform_test(joint)
    findings.append({
        'market': market, 'test': 'T1_joint_uniformity',
        'chi2': round(chi2, 2), 'df': df, 'p_value': p, 'n': int(joint.sum()),
        'top_cell': f'{mi // 10}{mi % 10}',
        'top_count': int(mc), 'expected': round(exp, 2),
        'top_lift_pct': round((mc / exp - 1) * 100, 2) if exp > 0 else 0,
    })

    # T2: Markov front
    m_f = np.zeros((10, 10))
    for i in range(1, n):
        m_f[fronts[i-1], fronts[i]] += 1
    chi2, df, p, v = chi_sq_indep_test(m_f)
    findings.append({
        'market': market, 'test': 'T2_markov_front',
        'chi2': round(chi2, 2), 'df': df, 'p_value': p,
        'cramers_v': round(v, 4), 'n': int(m_f.sum()),
        'best_conditional': best_conditional_cell(m_f),
    })

    # T3: Markov back
    m_b = np.zeros((10, 10))
    for i in range(1, n):
        m_b[backs[i-1], backs[i]] += 1
    chi2, df, p, v = chi_sq_indep_test(m_b)
    findings.append({
        'market': market, 'test': 'T3_markov_back',
        'chi2': round(chi2, 2), 'df': df, 'p_value': p,
        'cramers_v': round(v, 4), 'n': int(m_b.sum()),
        'best_conditional': best_conditional_cell(m_b),
    })

    # T4: Open last digit -> close back
    valid = opens >= 0
    if valid.sum() >= 200:
        ot, bt = opens[valid], backs[valid]
        tab = np.zeros((10, 10))
        for o, b in zip(ot, bt):
            tab[o, b] += 1
        chi2, df, p, v = chi_sq_indep_test(tab)
        findings.append({
            'market': market, 'test': 'T4_open_to_back',
            'chi2': round(chi2, 2), 'df': df, 'p_value': p,
            'cramers_v': round(v, 4), 'n': int(tab.sum()),
            'best_conditional': best_conditional_cell(tab),
        })

    # T5: Diff sign -> back
    sign = np.sign(diffs).astype(int) + 1
    tab = np.zeros((3, 10))
    for s, b in zip(sign, backs):
        tab[s, b] += 1
    nonzero = tab.sum(axis=1) >= 30
    if nonzero.sum() >= 2:
        tab_r = tab[nonzero]
        chi2, df, p, v = chi_sq_indep_test(tab_r)
        findings.append({
            'market': market, 'test': 'T5_diff_sign_to_back',
            'chi2': round(chi2, 2), 'df': df, 'p_value': p,
            'cramers_v': round(v, 4), 'n': int(tab_r.sum()),
            'best_conditional': best_conditional_cell(tab_r),
        })

    # T6: Diff quintile -> back
    abs_diff = np.abs(diffs)
    if (abs_diff > 0).sum() > 100:
        edges = np.percentile(abs_diff, [20, 40, 60, 80])
        bucket = np.digitize(abs_diff, edges)
        tab = np.zeros((5, 10))
        for q, b in zip(bucket, backs):
            tab[q, b] += 1
        chi2, df, p, v = chi_sq_indep_test(tab)
        findings.append({
            'market': market, 'test': 'T6_diff_quintile_to_back',
            'chi2': round(chi2, 2), 'df': df, 'p_value': p,
            'cramers_v': round(v, 4), 'n': int(tab.sum()),
            'best_conditional': best_conditional_cell(tab),
        })

    # T7: Sum (front+back) mod 10 uniformity
    sums = (fronts + backs) % 10
    counts = np.zeros(10)
    for s in sums:
        counts[s] += 1
    chi2, df, p, (mi, mc, exp) = chi_sq_uniform_test(counts)
    findings.append({
        'market': market, 'test': 'T7_sum_mod10_uniformity',
        'chi2': round(chi2, 2), 'df': df, 'p_value': p, 'n': int(counts.sum()),
        'top_value': int(mi), 'top_count': int(mc),
    })

    # T8: Autocorrelation back at lags 2, 3, 5, 7
    for lag in [2, 3, 5, 7]:
        if n - lag < 200:
            continue
        tab = np.zeros((10, 10))
        for i in range(lag, n):
            tab[backs[i-lag], backs[i]] += 1
        chi2, df, p, v = chi_sq_indep_test(tab)
        findings.append({
            'market': market, 'test': f'T8_back_autocorr_lag{lag}',
            'chi2': round(chi2, 2), 'df': df, 'p_value': p,
            'cramers_v': round(v, 4), 'n': int(tab.sum()),
        })

    # T9: Cross-lag: back[i] given front[i-1]
    cl_bf = np.zeros((10, 10))
    for i in range(1, n):
        cl_bf[fronts[i-1], backs[i]] += 1
    chi2, df, p, v = chi_sq_indep_test(cl_bf)
    findings.append({
        'market': market, 'test': 'T9_back_given_prev_front',
        'chi2': round(chi2, 2), 'df': df, 'p_value': p,
        'cramers_v': round(v, 4), 'n': int(cl_bf.sum()),
        'best_conditional': best_conditional_cell(cl_bf),
    })

    # T10: Cross-lag: front[i] given back[i-1]
    cl_fb = np.zeros((10, 10))
    for i in range(1, n):
        cl_fb[backs[i-1], fronts[i]] += 1
    chi2, df, p, v = chi_sq_indep_test(cl_fb)
    findings.append({
        'market': market, 'test': 'T10_front_given_prev_back',
        'chi2': round(chi2, 2), 'df': df, 'p_value': p,
        'cramers_v': round(v, 4), 'n': int(cl_fb.sum()),
        'best_conditional': best_conditional_cell(cl_fb),
    })

    return findings


def cross_market_tests(market_data):
    findings = []
    keys = list(market_data.keys())
    for m1, m2 in combinations(keys, 2):
        b1 = market_data[m1][1]
        b2 = market_data[m2][1]
        nmin = min(len(b1), len(b2))
        if nmin < 300:
            continue
        b1, b2 = b1[:nmin], b2[:nmin]
        tab = np.zeros((10, 10))
        for x, y in zip(b1, b2):
            tab[x, y] += 1
        chi2, df, p, v = chi_sq_indep_test(tab)
        findings.append({
            'market': f'{m1}_vs_{m2}',
            'test': 'T11_cross_market_back',
            'chi2': round(chi2, 2), 'df': df, 'p_value': p,
            'cramers_v': round(v, 4), 'n': nmin,
        })
    return findings


def assess_exploitability(finding):
    # Determine if a finding is large enough to overcome variance
    # Returns dict with verdict and recommended action
    bc = finding.get('best_conditional')
    if bc is None:
        return None

    cond_prob = bc.get('conditional_prob_pct', 0) / 100.0
    baseline = 0.10  # baseline for single back/front digit

    # For single-digit bet at 100x payout (front OR back), break-even = 1/100 = 1%
    # But per-position is 10% baseline
    # If we bet on the most likely digit at the most likely conditioning row:
    # Need cond_prob > break-even: need actual edge, not just statistical signal

    # Realistic break-even for single-digit single-position:
    # If betting only when condition matches, EV per bet:
    # win: cond_prob * 80, lose: (1 - cond_prob) * (-20)
    # EV = 80 * cond_prob - 20 * (1 - cond_prob) = 100 * cond_prob - 20
    # Break-even when 100 * cond_prob = 20 -> cond_prob = 0.20

    # Wait: this is for single digit picking at front position only or back only
    # Each draws 1 digit per position. If we bet 1 digit (1 number out of 10),
    # P(hit) = 0.10 baseline. Payout for that single-digit single-position bet
    # would need to be 10x to break even. We don't have that bet directly.

    # Most relevant: for "back" prediction with condition, useful if cond_prob
    # increases enough that betting top-2 digits at back position has WR > 20%.
    # Since baseline top-2 WR = 20%, need top digit prob > 10% by enough.

    # Simpler: just report cond_prob and lift, let user decide
    return {
        'conditional_prob_pct': round(cond_prob * 100, 2),
        'baseline_pct': round(baseline * 100, 2),
        'lift_over_baseline_pct': round((cond_prob - baseline) * 100, 2),
        'required_lift_for_2digit_edge': 'cond_prob > 12% (top-2 strategy)',
        'meaningful_edge': cond_prob > 0.12,
    }


def main():
    print('=' * 75)
    print('[Joint Diagnostic V2] Comprehensive Signal Search')
    print('=' * 75)

    raw_files = glob.glob(os.path.join(DATA_DIR, 'raw_*.json'))
    market_data = {}
    for fp in raw_files:
        if 'raw_excel' in fp:
            continue
        market = os.path.basename(fp).replace('raw_', '').replace('.json', '')
        with open(fp, 'r', encoding='utf-8') as f:
            draws = json.load(f)
        market_data[market] = parse_draws(draws)

    all_findings = []
    for market in market_data:
        f, b, d, o = market_data[market]
        print(f'[{market.upper()}] running 14 tests on n={len(f)} draws...')
        results = run_market_battery(market, f, b, d, o)
        all_findings.extend(results)

    print('\n[CROSS-MARKET] running pairwise correlation...')
    cross = cross_market_tests(market_data)
    all_findings.extend(cross)

    n_tests = len(all_findings)
    bonf_alpha = ALPHA / n_tests
    print(f'\nTotal tests: {n_tests}')
    print(f'Bonferroni alpha: {bonf_alpha:.6f}')

    for f in all_findings:
        f['bonferroni_p'] = round(min(1.0, f['p_value'] * n_tests), 6)
        f['significant'] = f['bonferroni_p'] < ALPHA
        f['exploitability'] = assess_exploitability(f)
        f['p_value'] = round(f['p_value'], 6)

    all_findings.sort(key=lambda x: x['p_value'])

    print('\n' + '=' * 75)
    print('TOP 20 LOWEST p-values (raw)')
    print('=' * 75)
    print(f"{'Sig':3s} {'Market':22s} {'Test':30s} {'p_raw':>8s} {'p_bonf':>8s} {'V':>6s}")
    print('-' * 75)
    for f in all_findings[:20]:
        sig = '***' if f['significant'] else '   '
        v = f.get('cramers_v', 0)
        print(f"{sig:3s} {f['market']:22s} {f['test']:30s} "
              f"{f['p_value']:8.4f} {f['bonferroni_p']:8.4f} {v:6.3f}")

    sig_findings = [f for f in all_findings if f['significant']]
    print('\n' + '=' * 75)
    if sig_findings:
        print(f'SIGNIFICANT FINDINGS ({len(sig_findings)} after Bonferroni correction)')
        print('=' * 75)
        for f in sig_findings:
            print(f"\n[{f['market']}] {f['test']}")
            print(f"  p_raw={f['p_value']:.6f}  p_bonf={f['bonferroni_p']:.6f}")
            if 'cramers_v' in f:
                print(f"  Cramers V: {f['cramers_v']:.4f}")
            if f.get('best_conditional'):
                bc = f['best_conditional']
                print(f"  Best cell: row={bc['row']} col={bc['col']} "
                      f"observed={bc['observed']} expected={bc['expected']:.1f} "
                      f"lift={bc['lift_pct']:+.1f}% cond_prob={bc['conditional_prob_pct']}%")
            if f.get('exploitability'):
                e = f['exploitability']
                marker = 'YES' if e['meaningful_edge'] else 'NO'
                print(f"  Exploitable edge? {marker}  "
                      f"cond_prob={e['conditional_prob_pct']}%  "
                      f"baseline={e['baseline_pct']}%  "
                      f"lift={e['lift_over_baseline_pct']:+.1f}pp")
    else:
        print('NO STATISTICALLY SIGNIFICANT FINDINGS')
        print('=' * 75)
        print('After Bonferroni correction across all dimensions tested:')
        print('  - Joint pair distributions')
        print('  - Markov 1st-order time dependencies (front and back)')
        print('  - Cross-position lag dependencies (NEW)')
        print('  - Open price -> close digit')
        print('  - Market direction (sign and magnitude) -> digit')
        print('  - Lagged autocorrelations (lags 2, 3, 5, 7)')
        print('  - Sum-mod-10 distribution')
        print('  - Cross-market same-day correlation')
        print('No exploitable signal detected.')
        print('Conclusion: this game is mathematically zero-EV.')

    report = {
        'n_tests': n_tests,
        'alpha': ALPHA,
        'bonferroni_alpha': bonf_alpha,
        'n_significant': len(sig_findings),
        'findings_sorted_by_p': all_findings,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2,
                  default=lambda o: float(o) if isinstance(o, np.floating) else str(o))
    print(f'\nFull report saved -> {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
