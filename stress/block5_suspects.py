#!/usr/bin/env python3 -I
"""
Block 5 — Known Suspects: targeted tests for the most dangerous silent failures.
S1: Y1 EPS proration, S2: two tax rates, S3: month-factor edge cases,
S5: mix disagreements, S7: AT self-trust, S9: sale table edge cases.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import run, run_baseline, compare, fmt_val, STRESS_DIR, OUTPUT_CELLS
from datetime import datetime
import json

FINDINGS = []

def finding(test_id, severity, classification, desc, evidence):
    f = {"test": test_id, "severity": severity, "class": classification,
         "desc": desc, "evidence": evidence}
    FINDINGS.append(f)
    marker = {"SILENT-WRONG": "🔴", "MISLEADING": "🟡", "LOUD-OK": "🟢",
              "CRASH": "⚪", "FALSE-ALARM": "🟠"}.get(classification, "⚫")
    print(f"  {marker} [{classification}] {desc}")
    if evidence:
        for k, v in evidence.items():
            print(f"      {k}: {v}")

def close(a, b, tol=0.005):
    if a is None or b is None: return a == b
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)): return False
    if a == 0: return abs(b) < tol
    return abs(b - a) / max(abs(a), 1e-10) < tol

print("=" * 70)
print("BLOCK 5 — KNOWN SUSPECTS")
print("=" * 70)

bl = run_baseline()
print(f"  Baseline: rate={fmt_val(bl['e3_allin_y1'])}, int={fmt_val(bl['e3_interest_y1'])}, EPS={fmt_val(bl['e4_eps_y1'])}")

# ═══ S1: Y1 EPS proration — does Y1 EPS jump with closing date? ═══
print("\n▸ S1: Y1 EPS proration by closing date")
closing_dates = [
    ("dec31", datetime(2026, 12, 31)),
    ("sep30", datetime(2026, 9, 30)),
    ("jun30", datetime(2026, 6, 30)),
    ("jan31", datetime(2026, 1, 31)),
]
s1_results = {}
for label, dt in closing_dates:
    r = run(f"S1_{label}", {
        "1. Deal Inputs!B20": dt,
        "1. Deal Inputs!B21": dt,
    })
    factor = (12 - dt.month) / 12
    s1_results[label] = {
        "eps": r.get('e4_eps_y1'),
        "ebit": r.get('e4_ebit_y1'),
        "net_finres": r.get('e4_net_finres_y1'),
        "interest": r.get('e3_interest_y1'),
        "factor": factor,
    }
    print(f"    {label}: factor={factor:.3f}, EPS={fmt_val(r.get('e4_eps_y1'))}, "
          f"EBIT={fmt_val(r.get('e4_ebit_y1'))}, interest={fmt_val(r.get('e3_interest_y1'))}")

# EPS = (EBIT × (1-tax) + FinRes × (1-shield_tax) - WHT) / shares
# EBIT is FULL YEAR but interest is prorated. So as closing gets later,
# interest drops but EBIT stays full → EPS jumps.
# This is the known distortion.
dec_eps = s1_results['dec31']['eps']
sep_eps = s1_results['sep30']['eps']
jan_eps = s1_results['jan31']['eps']
if dec_eps is not None and jan_eps is not None and isinstance(dec_eps, (int,float)) and isinstance(jan_eps, (int,float)):
    eps_range = abs(jan_eps - dec_eps)
    finding("S1", "MEDIUM", "MISLEADING",
            f"Y1 EPS swings €{eps_range:.4f}/share from Jan to Dec closing "
            f"(EBIT full-year, interest prorated)",
            {"jan31_eps": fmt_val(jan_eps), "sep30_eps": fmt_val(sep_eps),
             "dec31_eps": fmt_val(dec_eps),
             "jan31_ebit": fmt_val(s1_results['jan31']['ebit']),
             "dec31_ebit": fmt_val(s1_results['dec31']['ebit']),
             "note": "EBIT is always full year; only financing prorated"})
else:
    finding("S1", "MEDIUM", "CRASH", "Could not compute EPS range", {"results": str(s1_results)[:300]})

# ═══ S2: Two tax rates — which outputs move? ═══
print("\n▸ S2: Two tax rates — which moves what?")
# B42 = Group/target operating tax rate (→ E4 C56 Deal net income: EBIT×(1-B42))
# 2. Target Plan B14 = cash tax (→ Henkel Summary C41)
s2a = run("S2a_op_tax_30pct", {"1. Deal Inputs!B42": 0.30})
s2b = run("S2b_op_tax_15pct", {"1. Deal Inputs!B42": 0.15})
# Change B42 → E4 EPS should change, E3 interest should NOT change
int_moved = not close(bl['e3_interest_y1'], s2a['e3_interest_y1'])
eps_moved = not close(bl['e4_eps_y1'], s2a['e4_eps_y1'])
finding("S2", "info", "LOUD-OK" if (eps_moved and not int_moved) else "SILENT-WRONG",
        f"Operating tax B42: changes EPS={eps_moved}, changes interest={int_moved}",
        {"bl_eps": fmt_val(bl['e4_eps_y1']), "30pct_eps": fmt_val(s2a['e4_eps_y1']),
         "15pct_eps": fmt_val(s2b['e4_eps_y1']),
         "bl_int": fmt_val(bl['e3_interest_y1']), "30pct_int": fmt_val(s2a['e3_interest_y1'])})

# ═══ S3: Month-factor edge cases ═══
print("\n▸ S3: Month-factor edge cases")
# B24 = (12 - MONTH(close))/12
# Month 12 → factor = 0 → Y1 interest = 0
# Does this cause DIV/0 anywhere?
s3_dec = run("S3_month12", {
    "1. Deal Inputs!B20": datetime(2026, 12, 15),
    "1. Deal Inputs!B21": datetime(2026, 12, 15),
})
# Check for crashes and zero-interest edge cases
if s3_dec.get('e3_interest_y1') == 0:
    # Check if this causes issues downstream
    at_ok = s3_dec.get('at_failing', 99) == 0
    finding("S3", "MEDIUM" if not at_ok else "LOW",
            "MISLEADING" if at_ok else "FALSE-ALARM",
            f"Dec closing: Y1 interest=0 (factor=0), AT {'pass' if at_ok else 'fail'}",
            {"interest_y1": s3_dec['e3_interest_y1'],
             "at_failing": s3_dec.get('at_failing'),
             "eps_y1": fmt_val(s3_dec.get('e4_eps_y1')),
             "note": "month=12→factor=0→interest=0 but deal is funded"})
else:
    finding("S3", "info", "LOUD-OK",
            f"Dec closing: interest={fmt_val(s3_dec.get('e3_interest_y1'))}",
            {"factor": "(12-12)/12=0 expected", "actual_int": fmt_val(s3_dec.get('e3_interest_y1'))})

# Mid-month: does day matter?
s3_mid = run("S3_mid_month", {
    "1. Deal Inputs!B20": datetime(2026, 9, 15),
    "1. Deal Inputs!B21": datetime(2026, 9, 15),
})
# Compare to Sep30 baseline — should be identical since formula uses MONTH only
if close(bl['e3_interest_y1'], s3_mid['e3_interest_y1']):
    finding("S3b", "LOW", "MISLEADING",
            "Mid-month (Sep15) = end-of-month (Sep30) — day ignored, only MONTH used",
            {"sep15_int": fmt_val(s3_mid['e3_interest_y1']),
             "sep30_int": fmt_val(bl['e3_interest_y1']),
             "note": "15 days of additional interest lost"})
else:
    finding("S3b", "info", "LOUD-OK",
            "Mid-month closing gives different interest (day-level proration)",
            {"sep15_int": fmt_val(s3_mid['e3_interest_y1']),
             "sep30_int": fmt_val(bl['e3_interest_y1'])})

# ═══ S5: Mix disagreements ═══
print("\n▸ S5: Three-way mix disagreement")
# ccy mix (tab 3) vs instrument table vs entity routes
# Put a ccy in the mix that has no entity route
# The baseline has EUR + USD entities. Let's add GBP to the ccy mix
s5 = run("S5_ccy_no_entity", {
    "3. Scenario & Mix!A8": "EUR",
    "3. Scenario & Mix!C8": 0.5,  # 50% EUR
    "3. Scenario & Mix!A9": "USD",
    "3. Scenario & Mix!C9": 0.3,  # 30% USD
    "3. Scenario & Mix!A10": "GBP",
    "3. Scenario & Mix!C10": 0.2,  # 20% GBP — no entity for GBP
})
# Does anything warn? Or does GBP silently get no entity/tax treatment?
at_ok = s5.get('at_failing', 99) == 0
finding("S5", "HIGH" if at_ok else "MEDIUM",
        "SILENT-WRONG" if at_ok else "LOUD-OK",
        f"GBP in mix with no entity route: AT {'all pass (no warning!)' if at_ok else 'flags it'}",
        {"at_failing": s5.get('at_failing'),
         "at_verdict": str(s5.get('at_verdict'))[:100],
         "failing_list": str(s5.get('_at_failing_list', []))[:300]})

# ═══ S7: Acceptance Test self-trust ═══
print("\n▸ S7: AT self-trust — break things the AT claims to check")
# Overwrite E3 C65 (interest Y1) with a hardcode
import openpyxl
import shutil

# Test 1: Hardcode E3 C65 (interest) to a wrong value
s7a = run("S7a_hardcode_interest", {
    "E3 · Cost & Schedule!C65": 999.99,  # Clearly wrong interest
})
at_caught = s7a.get('at_failing', 0) > 0
finding("S7a", "HIGH" if not at_caught else "info",
        "SILENT-WRONG" if not at_caught else "LOUD-OK",
        f"Hardcoded E3!C65=999.99: AT {'catches it' if at_caught else 'MISSES IT (blind spot!)'}",
        {"at_failing": s7a.get('at_failing'),
         "at_verdict": str(s7a.get('at_verdict'))[:100],
         "failing": str(s7a.get('_at_failing_list', []))[:300]})

# Test 2: Hardcode the all-in rate
s7b = run("S7b_hardcode_rate", {
    "E3 · Cost & Schedule!C54": 0.99,  # 99% all-in rate
})
at_caught2 = s7b.get('at_failing', 0) > 0
finding("S7b", "HIGH" if not at_caught2 else "info",
        "SILENT-WRONG" if not at_caught2 else "LOUD-OK",
        f"Hardcoded E3!C54=99%: AT {'catches it' if at_caught2 else 'MISSES IT'}",
        {"at_failing": s7b.get('at_failing'),
         "at_verdict": str(s7b.get('at_verdict'))[:100],
         "failing": str(s7b.get('_at_failing_list', []))[:300]})

# Test 3: Hardcode EPS
s7c = run("S7c_hardcode_eps", {
    "E4 · KPIs & Funding!C57": 5.00,  # €5/share EPS (clearly wrong)
})
at_caught3 = s7c.get('at_failing', 0) > 0
finding("S7c", "HIGH" if not at_caught3 else "info",
        "SILENT-WRONG" if not at_caught3 else "LOUD-OK",
        f"Hardcoded E4!C57=€5/share: AT {'catches it' if at_caught3 else 'MISSES IT'}",
        {"at_failing": s7c.get('at_failing'),
         "at_verdict": str(s7c.get('at_verdict'))[:100]})

# Test 4: Hardcode the AT verdict itself
s7d = run("S7d_hardcode_verdict", {
    "✓ Acceptance Test!B5": 0,  # Force "0 checks failing"
    "✓ Acceptance Test!B6": "✅ ALL CHECKS PASS — FAKE",
})
# This should ALWAYS succeed since we're overwriting the verdict cell itself
# The question is: does anything else catch it?
finding("S7d", "LOW", "MISLEADING",
        "Hardcoded AT verdict cell: verdict says PASS but is a hardcode",
        {"note": "AT cell B5/B6 can be overwritten — no protection"})

# ═══ S9: Sale table edge cases ═══
print("\n▸ S9: Sale table edge cases")

# S9a: Lower-case ISO code
s9a = run("S9a_lowercase_iso", {
    "3. Scenario & Mix!A86": "eur",  # lowercase
    "3. Scenario & Mix!B86": 0.5,
    "3. Scenario & Mix!C86": 3,
})
# Does the model match "eur" to "EUR"?
at_ok_9a = s9a.get('at_failing', 99) == 0
interest_shed = s9a.get('hs_interest_shed', 0)
finding("S9a", "MEDIUM" if at_ok_9a and (interest_shed == 0 or interest_shed is None) else "info",
        "SILENT-WRONG" if at_ok_9a and (interest_shed == 0 or interest_shed is None) else "LOUD-OK",
        f"Lowercase 'eur': shed={fmt_val(interest_shed)}, AT {'pass' if at_ok_9a else 'fail'}",
        {"shed": interest_shed, "at": s9a.get('at_failing'),
         "note": "lowercase ISO should match EUR leg" if interest_shed == 0 else ""})

# S9b: Event year 0
s9b = run("S9b_event_year_0", {
    "3. Scenario & Mix!A86": "EUR",
    "3. Scenario & Mix!B86": 0.5,
    "3. Scenario & Mix!C86": 0,  # Year 0 — invalid
})
at_ok_9b = s9b.get('at_failing', 99) == 0
finding("S9b", "MEDIUM" if at_ok_9b else "info",
        "SILENT-WRONG" if at_ok_9b else "LOUD-OK",
        f"Event year 0: AT {'pass (no warning!)' if at_ok_9b else 'catches it'}",
        {"at_failing": s9b.get('at_failing'),
         "shed": fmt_val(s9b.get('hs_interest_shed'))})

# S9c: Event year 9 (beyond horizon 8)
s9c = run("S9c_event_year_9", {
    "3. Scenario & Mix!A86": "EUR",
    "3. Scenario & Mix!B86": 0.5,
    "3. Scenario & Mix!C86": 9,  # Beyond horizon
})
at_ok_9c = s9c.get('at_failing', 99) == 0
finding("S9c", "MEDIUM" if at_ok_9c else "info",
        "SILENT-WRONG" if at_ok_9c else "LOUD-OK",
        f"Event year 9 (beyond horizon 8): AT {'pass (inert sale?)' if at_ok_9c else 'flags'}",
        {"shed": fmt_val(s9c.get('hs_interest_shed')),
         "at": s9c.get('at_failing')})

# S9d: EBIT share > 100%
s9d = run("S9d_ebit_share_150pct", {
    "3. Scenario & Mix!A86": "EUR",
    "3. Scenario & Mix!B86": 0.5,
    "3. Scenario & Mix!C86": 3,
    "3. Scenario & Mix!D86": 1.5,  # 150% EBIT share — nonsense
})
at_ok_9d = s9d.get('at_failing', 99) == 0
op_retained = s9d.get('hs_op_retained')
finding("S9d", "MEDIUM" if (at_ok_9d and op_retained is not None and op_retained < 0) else "info",
        "SILENT-WRONG" if (at_ok_9d and op_retained is not None and op_retained < 0) else "LOUD-OK",
        f"EBIT share 150%: op_retained={fmt_val(op_retained)}, AT {'pass' if at_ok_9d else 'fail'}",
        {"op_retained": op_retained, "at": s9d.get('at_failing')})

# S9e: Funding-only (B65=N) with EBIT share filled
s9e = run("S9e_funding_only_ebit", {
    "1. Deal Inputs!B65": "N",
    "3. Scenario & Mix!A86": "EUR",
    "3. Scenario & Mix!B86": 0.5,
    "3. Scenario & Mix!C86": 3,
    "3. Scenario & Mix!D86": 0.3,  # EBIT share on funding-only sale
})
op_retained_e = s9e.get('hs_op_retained')
finding("S9e", "LOW" if op_retained_e == 1 else "MEDIUM",
        "LOUD-OK" if op_retained_e == 1 else "SILENT-WRONG",
        f"Funding-only (B65=N) with EBIT D=30%: op_retained={fmt_val(op_retained_e)}",
        {"op_retained": op_retained_e,
         "note": "B65=N should ignore EBIT share (operating side stays 100%)"})

# ═══ SUMMARY ═══
print("\n" + "=" * 70)
print("BLOCK 5 SUMMARY")
print("=" * 70)
for cls in ["SILENT-WRONG", "CRASH", "MISLEADING", "FALSE-ALARM", "LOUD-OK"]:
    items = [f for f in FINDINGS if f['class'] == cls]
    if items:
        icon = {"SILENT-WRONG": "🔴", "CRASH": "⚪", "MISLEADING": "🟡",
                "FALSE-ALARM": "🟠", "LOUD-OK": "🟢"}[cls]
        print(f"\n  {icon} {cls} ({len(items)}):")
        for f in items:
            print(f"    {f['test']}: {f['desc'][:100]}")

with open(STRESS_DIR / "block5_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
print(f"\nFindings saved to {STRESS_DIR / 'block5_findings.json'}")
