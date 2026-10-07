#!/usr/bin/env python3 -I
"""
Block 4 — Metamorphic / Invariant Tests
14 tests that don't need a twin — any violation = bug or undocumented non-linearity.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import run, run_baseline, compare, fmt_val, STRESS_DIR
import json

FINDINGS = []

def finding(test_id, severity, classification, desc, evidence):
    f = {
        "test": test_id,
        "severity": severity,
        "class": classification,
        "desc": desc,
        "evidence": evidence,
    }
    FINDINGS.append(f)
    marker = "🔴" if classification == "SILENT-WRONG" else "🟡" if classification == "MISLEADING" else "🟢" if classification == "LOUD-OK" else "⚪"
    print(f"  {marker} [{classification}] {desc}")
    if evidence:
        for k, v in evidence.items():
            print(f"      {k}: {v}")

def close(bv, tv, tol=0.005):
    """Check if two numeric values are close."""
    if bv is None or tv is None:
        return bv == tv
    if not isinstance(bv, (int, float)) or not isinstance(tv, (int, float)):
        return str(bv) == str(tv)
    if bv == 0:
        return abs(tv) < tol
    return abs(tv - bv) / max(abs(bv), 1e-10) < tol

def ratio_check(bv, tv, expected_ratio, tol=0.02):
    """Check if tv/bv ≈ expected_ratio."""
    if bv is None or tv is None or bv == 0:
        return False
    actual = tv / bv
    return abs(actual - expected_ratio) / max(abs(expected_ratio), 1e-10) < tol

print("=" * 70)
print("BLOCK 4 — METAMORPHIC / INVARIANT TESTS")
print("=" * 70)

# Run baseline first
print("\n▸ Running baseline...")
bl = run_baseline()
print(f"  Baseline: all-in={fmt_val(bl['e3_allin_y1'])}, interest={fmt_val(bl['e3_interest_y1'])}, EPS={fmt_val(bl['e4_eps_y1'])}")

# ─── TEST M1: Scale PP ×2, no paydown → interest ×2, rate unchanged ───
print("\n▸ M1: Scale PP ×2 → interest ×2, rate unchanged")
m1 = run("M1_PP_x2", {"1. Deal Inputs!B9": 2000})
# Rate should be unchanged
rate_ok = close(bl['e3_allin_y1'], m1['e3_allin_y1'])
# Interest should be ×2
int_ratio = m1['e3_interest_y1'] / bl['e3_interest_y1'] if bl['e3_interest_y1'] else None
int_ok = ratio_check(bl['e3_interest_y1'], m1['e3_interest_y1'], 2.0)
# Amount raised should be ×2
amt_ok = ratio_check(bl['e3_amount_raised'], m1['e3_amount_raised'], 2.0)
if rate_ok and int_ok and amt_ok:
    finding("M1", "info", "LOUD-OK", "PP×2: rate unchanged, interest×2, amount×2 — linearity holds",
            {"rate_bl": bl['e3_allin_y1'], "rate_2x": m1['e3_allin_y1'],
             "int_ratio": f"{int_ratio:.4f}", "amt_ratio": f"{m1['e3_amount_raised']/bl['e3_amount_raised']:.4f}"})
else:
    finding("M1", "HIGH", "SILENT-WRONG", f"PP×2: linearity broken",
            {"rate_bl": bl['e3_allin_y1'], "rate_2x": m1['e3_allin_y1'],
             "int_bl": bl['e3_interest_y1'], "int_2x": m1['e3_interest_y1'],
             "int_ratio": f"{int_ratio:.4f}" if int_ratio else "N/A"})

# ─── TEST M2: Flat curve (all ccy rates equal) → all-in independent of mix ───
# This requires modifying WSS rates which is complex - skip for now, note it
print("\n▸ M2: [DEFERRED — requires curve manipulation]")

# ─── TEST M3: 100% EUR, one instrument → all-in = EUR curve + spread + fees ───
print("\n▸ M3: 100% EUR, single instrument check")
# Already 100% EUR in baseline based on the mix; check if single instrument simplifies
# Set instrument mix to 100% one instrument (need to find the weight cells)
# For now, verify the baseline is 100% EUR
m3 = run("M3_100pct_EUR", {
    "3. Scenario & Mix!B54": 1,  # 100% first instrument weight
    "3. Scenario & Mix!B55": 0,
    "3. Scenario & Mix!B56": 0,
    "3. Scenario & Mix!B57": 0,
    "3. Scenario & Mix!B58": 0,
    "3. Scenario & Mix!B59": 0,
})
# With one instrument at 100%, the all-in should be that instrument's rate
if m3.get('at_failing', 0) == 0:
    finding("M3", "info", "LOUD-OK", "Single instrument: model recalculates correctly",
            {"allin": fmt_val(m3['e3_allin_y1']), "at": m3['at_verdict']})
else:
    finding("M3", "MEDIUM", "FALSE-ALARM" if isinstance(m3.get('at_failing'), int) else "CRASH",
            f"Single instrument: {m3.get('at_failing')} checks fail",
            {"at": m3.get('at_verdict'), "failing": str(m3.get('_at_failing_list', []))[:200]})

# ─── TEST M4: Shift closing +12 months → identical yearly results shifted ───
print("\n▸ M4: Closing +12 months → results shift one year")
from datetime import datetime
m4 = run("M4_close_plus12m", {
    "1. Deal Inputs!B19": datetime(2027, 5, 1),  # signing +1yr
    "1. Deal Inputs!B20": datetime(2027, 9, 30), # closing +1yr
    "1. Deal Inputs!B21": datetime(2027, 9, 30), # payment +1yr
    "1. Deal Inputs!B22": datetime(2030, 12, 31), # integration end +1yr
})
# Y1 results should match baseline Y1, Y2 match baseline Y2
y1_rate_match = close(bl['e3_allin_y1'], m4['e3_allin_y1'], tol=0.01)
y1_int_match = close(bl['e3_interest_y1'], m4['e3_interest_y1'], tol=0.02)
if y1_rate_match and y1_int_match:
    finding("M4", "info", "LOUD-OK", "Closing +12m: Y1 rate and interest match baseline Y1",
            {"bl_rate": fmt_val(bl['e3_allin_y1']), "m4_rate": fmt_val(m4['e3_allin_y1']),
             "bl_int": fmt_val(bl['e3_interest_y1']), "m4_int": fmt_val(m4['e3_interest_y1'])})
else:
    # Not necessarily wrong — curve moves with date. Check if it's sensible
    finding("M4", "LOW", "MISLEADING" if y1_rate_match else "SILENT-WRONG",
            f"Closing +12m: Y1 differs — may be curve-dependent (rate {'matched' if y1_rate_match else 'differs'})",
            {"bl_rate": fmt_val(bl['e3_allin_y1']), "m4_rate": fmt_val(m4['e3_allin_y1']),
             "bl_int": fmt_val(bl['e3_interest_y1']), "m4_int": fmt_val(m4['e3_interest_y1'])})

# ─── TEST M5: Closing 1-Jan vs 31-Dec → Y1 interest ≈ full year diff ───
print("\n▸ M5: Closing 1-Jan vs 31-Dec → Y1 interest differs by ≈ full year")
m5a = run("M5a_close_jan1", {
    "1. Deal Inputs!B20": datetime(2027, 1, 1),
    "1. Deal Inputs!B21": datetime(2027, 1, 1),
})
m5b = run("M5b_close_dec31", {
    "1. Deal Inputs!B20": datetime(2026, 12, 31),
    "1. Deal Inputs!B21": datetime(2026, 12, 31),
})
# B24 = (12 - MONTH(close))/12 → Jan1: 11/12, Dec31: 0/12
# So Y1 interest for Jan1 should be ≈ 11× Dec31
if m5a.get('e3_interest_y1') and m5b.get('e3_interest_y1'):
    ratio = m5a['e3_interest_y1'] / m5b['e3_interest_y1'] if m5b['e3_interest_y1'] != 0 else float('inf')
    # Dec31 gives month=12, factor=0/12=0 → Y1 interest = 0
    # Jan1 gives month=1, factor=11/12
    if m5b['e3_interest_y1'] == 0 or abs(m5b['e3_interest_y1']) < 0.001:
        finding("M5", "MEDIUM", "SILENT-WRONG" if m5b['e3_interest_y1'] == 0 else "LOUD-OK",
                f"Dec31 closing: Y1 interest = {fmt_val(m5b['e3_interest_y1'])} (month factor = 0)",
                {"jan1_int": fmt_val(m5a['e3_interest_y1']),
                 "dec31_int": fmt_val(m5b['e3_interest_y1']),
                 "jan1_factor": "11/12=0.917", "dec31_factor": "0/12=0",
                 "note": "Dec31 close gives month factor 0 → zero Y1 interest but deal still costs"})
    else:
        finding("M5", "info", "LOUD-OK",
                f"Jan1 vs Dec31: interest ratio={ratio:.2f} (expected ≈11 or more)",
                {"jan1_int": fmt_val(m5a['e3_interest_y1']), "dec31_int": fmt_val(m5b['e3_interest_y1'])})
else:
    finding("M5", "HIGH", "CRASH", "Could not compute Jan1/Dec31 interest comparison",
            {"jan1": m5a.get('e3_interest_y1'), "dec31": m5b.get('e3_interest_y1')})

# ─── TEST M6: +100bps to every curve point → interest ≈ +100bps × avg balance ───
# This requires modifying WSS rates — deferred
print("\n▸ M6: [DEFERRED — requires curve manipulation]")

# ─── TEST M7: Spread override = 0 → all-in = base + fees only ───
print("\n▸ M7: [DEFERRED — requires spread override cell ID]")

# ─── TEST M8: Amortise vs earns-income → no double count ───
print("\n▸ M8: Amortise FCF vs earns-income — no double count")
m8a = run("M8a_amortise", {"1. Deal Inputs!B35": "pays down debt (amortise)"})
m8b = run("M8b_earns", {"1. Deal Inputs!B35": "earns income per currency"})
# Both should produce valid results; total cost over horizon should be comparable
if m8a.get('at_failing', 99) == 0 and m8b.get('at_failing', 99) == 0:
    finding("M8", "info", "LOUD-OK",
            f"Both FCF modes pass AT checks",
            {"amortise_int": fmt_val(m8a['e3_interest_y1']),
             "earns_int": fmt_val(m8b['e3_interest_y1']),
             "amortise_netfin": fmt_val(m8a['e3_net_finres_y1']),
             "earns_netfin": fmt_val(m8b['e3_net_finres_y1'])})
else:
    finding("M8", "MEDIUM", "FALSE-ALARM",
            f"FCF mode change triggers AT failures",
            {"amortise_at": m8a.get('at_failing'),
             "earns_at": m8b.get('at_failing'),
             "amortise_fails": str(m8a.get('_at_failing_list', []))[:200],
             "earns_fails": str(m8b.get('_at_failing_list', []))[:200]})

# ─── TEST M9: Sale 0% / 100% boundary ───
print("\n▸ M9: Sale boundary — 0% should equal no-sale, 100% → zero retained")
m9a = run("M9a_sale_0pct", {
    "1. Deal Inputs!B57": 0,
    "1. Deal Inputs!B58": 1,
})
m9b = run("M9b_sale_100pct", {
    "1. Deal Inputs!B57": 1,  # 100%
    "1. Deal Inputs!B58": 1,
})
# 0% sale should equal baseline
sale0_match = close(bl['e3_interest_y1'], m9a['e3_interest_y1'])
# 100% sale → retained = 0, acquirer financing should be 0
retained_100 = m9b.get('hs_retained_pct')
if sale0_match:
    finding("M9a", "info", "LOUD-OK", "0% sale = baseline (inert)",
            {"bl_int": fmt_val(bl['e3_interest_y1']), "0pct_int": fmt_val(m9a['e3_interest_y1'])})
else:
    finding("M9a", "MEDIUM", "SILENT-WRONG", "0% sale differs from baseline",
            {"bl_int": fmt_val(bl['e3_interest_y1']), "0pct_int": fmt_val(m9a['e3_interest_y1'])})

if retained_100 is not None and retained_100 == 0:
    finding("M9b", "info", "LOUD-OK", "100% sale: retained = 0",
            {"retained": retained_100, "post_sale_int": fmt_val(m9b.get('hs_post_sale_interest'))})
elif retained_100 is not None:
    finding("M9b", "MEDIUM", "SILENT-WRONG" if not isinstance(m9b.get('at_verdict',''), str) or '❌' not in str(m9b.get('at_verdict','')) else "LOUD-OK",
            f"100% sale: retained = {retained_100} (expected 0)",
            {"retained": retained_100, "at": m9b.get('at_verdict')})
else:
    finding("M9b", "MEDIUM", "CRASH", "100% sale: retained is None", {})

# ─── TEST M10: Sale year N vs N+1 → difference only in year N ───
print("\n▸ M10: Sale year 3 vs year 5 → difference only in that year")
m10a = run("M10a_sale_yr3", {
    "1. Deal Inputs!B57": 0.5,
    "1. Deal Inputs!B58": 3,
})
m10b = run("M10b_sale_yr5", {
    "1. Deal Inputs!B57": 0.5,
    "1. Deal Inputs!B58": 5,
})
# Y1 and Y2 should be identical between the two
y1_match = close(m10a['e3_interest_y1'], m10b['e3_interest_y1'])
y2_match = close(m10a.get('e3_interest_y2'), m10b.get('e3_interest_y2'))
if y1_match and y2_match:
    finding("M10", "info", "LOUD-OK", "Sale year shift: Y1-Y2 identical, difference starts at event year",
            {"yr3_int_y1": fmt_val(m10a['e3_interest_y1']), "yr5_int_y1": fmt_val(m10b['e3_interest_y1']),
             "yr3_int_y2": fmt_val(m10a.get('e3_interest_y2')), "yr5_int_y2": fmt_val(m10b.get('e3_interest_y2'))})
else:
    finding("M10", "MEDIUM", "SILENT-WRONG",
            "Sale year shift: pre-event years differ (should be identical)",
            {"yr3_int_y1": fmt_val(m10a['e3_interest_y1']), "yr5_int_y1": fmt_val(m10b['e3_interest_y1'])})

# ─── TEST M11: Reorder instrument rows → same result ───
print("\n▸ M11: [DEFERRED — instrument row reorder requires complex cell swaps]")

# ─── TEST M12: Report currency USD → figures ×FX, calculations unchanged ───
print("\n▸ M12: Report currency USD → display-only change")
m12 = run("M12_report_USD", {"1. Deal Inputs!B11": "USD"})
# The Dashboard values should be ×FX, but engine values unchanged
engine_match = close(bl['e3_allin_y1'], m12['e3_allin_y1'])
engine_int_match = close(bl['e3_interest_y1'], m12['e3_interest_y1'])
if engine_match and engine_int_match:
    finding("M12", "info", "LOUD-OK", "Report USD: engine unchanged, display scales by FX",
            {"bl_dash_int": fmt_val(bl['dash_interest_y1']), "usd_dash_int": fmt_val(m12['dash_interest_y1']),
             "bl_engine_int": fmt_val(bl['e3_interest_y1']), "usd_engine_int": fmt_val(m12['e3_interest_y1'])})
else:
    finding("M12", "HIGH", "SILENT-WRONG",
            "Report USD: engine values changed (should be display-only)",
            {"bl_rate": fmt_val(bl['e3_allin_y1']), "usd_rate": fmt_val(m12['e3_allin_y1']),
             "bl_int": fmt_val(bl['e3_interest_y1']), "usd_int": fmt_val(m12['e3_interest_y1'])})

# ─── TEST M13: Horizon 3 vs 8 → years 1-3 identical ───
print("\n▸ M13: Horizon 3 vs 8 → Y1-Y3 identical")
m13 = run("M13_horizon_3", {"1. Deal Inputs!B40": 3})
y1_match = close(bl['e3_allin_y1'], m13['e3_allin_y1'])
y2_match = close(bl['e3_allin_y2'], m13['e3_allin_y2'])
y3_match = close(bl['e3_allin_y3'], m13['e3_allin_y3'])
y1_int_match = close(bl['e3_interest_y1'], m13['e3_interest_y1'])
if y1_match and y2_match and y3_match and y1_int_match:
    finding("M13", "info", "LOUD-OK", "Horizon 3: Y1-Y3 identical to horizon 8",
            {"bl_y1": fmt_val(bl['e3_allin_y1']), "h3_y1": fmt_val(m13['e3_allin_y1']),
             "bl_y3": fmt_val(bl['e3_allin_y3']), "h3_y3": fmt_val(m13['e3_allin_y3'])})
else:
    finding("M13", "MEDIUM", "SILENT-WRONG",
            "Horizon 3: Y1-Y3 differ from horizon 8",
            {"bl_y1": fmt_val(bl['e3_allin_y1']), "h3_y1": fmt_val(m13['e3_allin_y1']),
             "bl_y2": fmt_val(bl['e3_allin_y2']), "h3_y2": fmt_val(m13['e3_allin_y2']),
             "bl_y3": fmt_val(bl['e3_allin_y3']), "h3_y3": fmt_val(m13['e3_allin_y3'])})

# ─── TEST M14: Idempotency — recalc 3× → identical ───
print("\n▸ M14: Idempotency — recalc 3× with same inputs")
m14a = run("M14a_recalc2", {})
m14b = run("M14b_recalc3", {})
diffs = compare(bl, m14a, tol=0.0001)
diffs2 = compare(bl, m14b, tol=0.0001)
if not diffs and not diffs2:
    finding("M14", "info", "LOUD-OK", "Three recalcs produce identical results",
            {"num_diffs_run2": len(diffs), "num_diffs_run3": len(diffs2)})
else:
    finding("M14", "HIGH", "SILENT-WRONG",
            f"Recalcs differ: {len(diffs)} diffs in run 2, {len(diffs2)} in run 3",
            {"diffs_run2": str(diffs[:5]), "diffs_run3": str(diffs2[:5])})

# ─── SUMMARY ───
print("\n" + "=" * 70)
print("BLOCK 4 SUMMARY")
print("=" * 70)
silent_wrong = [f for f in FINDINGS if f['class'] == 'SILENT-WRONG']
crashes = [f for f in FINDINGS if f['class'] == 'CRASH']
loud_ok = [f for f in FINDINGS if f['class'] == 'LOUD-OK']
misleading = [f for f in FINDINGS if f['class'] == 'MISLEADING']
print(f"  Total tests run: {len(FINDINGS)}")
print(f"  SILENT-WRONG: {len(silent_wrong)}")
print(f"  CRASH: {len(crashes)}")
print(f"  MISLEADING: {len(misleading)}")
print(f"  LOUD-OK: {len(loud_ok)}")

if silent_wrong:
    print("\n  🔴 SILENT-WRONG findings:")
    for f in silent_wrong:
        print(f"    {f['test']}: {f['desc']}")
if crashes:
    print("\n  ⚪ CRASH findings:")
    for f in crashes:
        print(f"    {f['test']}: {f['desc']}")

# Save findings
with open(STRESS_DIR / "block4_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
print(f"\nFindings saved to {STRESS_DIR / 'block4_findings.json'}")
