#!/usr/bin/env python3 -I
"""
Block 6 — Reviewer-Experience Stress.
Tests whether dashboard/summary agree with engine tabs, and whether
displayed values match underlying calculations.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import run, run_baseline, compare, fmt_val, STRESS_DIR
import json

FINDINGS = []

def finding(test_id, severity, classification, desc, evidence):
    f = {"test": test_id, "severity": severity, "class": classification,
         "desc": desc, "evidence": evidence}
    FINDINGS.append(f)
    marker = {"SILENT-WRONG": "🔴", "MISLEADING": "🟡", "LOUD-OK": "🟢",
              "CRASH": "⚪", "FALSE-ALARM": "🟠"}.get(classification, "⚫")
    print(f"  {marker} [{classification}] {desc}")

print("=" * 70)
print("BLOCK 6 — REVIEWER-EXPERIENCE STRESS")
print("=" * 70)

bl = run_baseline()

# ── R1: Dashboard vs Engine tab consistency ──
print("\n▸ R1: Dashboard vs E3 engine consistency")
dash_rate = bl.get('dash_allin_y1')
e3_rate = bl.get('e3_allin_y1')
dash_amount = bl.get('dash_amount_raised')
e3_amount = bl.get('e3_amount_raised')
dash_interest = bl.get('dash_interest_y1')
e3_interest = bl.get('e3_interest_y1')

mismatches = []
if isinstance(dash_rate, (int,float)) and isinstance(e3_rate, (int,float)):
    if abs(dash_rate - e3_rate) > 0.0001:
        mismatches.append(("rate", dash_rate, e3_rate))
if isinstance(dash_amount, (int,float)) and isinstance(e3_amount, (int,float)):
    if abs(dash_amount - e3_amount) > 0.01:
        mismatches.append(("amount", dash_amount, e3_amount))
if isinstance(dash_interest, (int,float)) and isinstance(e3_interest, (int,float)):
    if abs(dash_interest - e3_interest) > 0.01:
        mismatches.append(("interest", dash_interest, e3_interest))

if mismatches:
    finding("R1_dash_engine", "HIGH", "SILENT-WRONG",
            f"Dashboard disagrees with E3 engine: {mismatches}",
            {"mismatches": mismatches})
else:
    finding("R1_dash_engine", "info", "LOUD-OK",
            "Dashboard matches E3 engine outputs",
            {"dash_rate": fmt_val(dash_rate), "e3_rate": fmt_val(e3_rate)})

# ── R2: Dashboard vs E4 EPS consistency ──
print("\n▸ R2: Dashboard vs E4 EPS consistency")
dash_eps = bl.get('dash_eps_y1')
e4_eps = bl.get('e4_eps_y1')
if isinstance(dash_eps, (int,float)) and isinstance(e4_eps, (int,float)):
    if abs(dash_eps - e4_eps) > 0.001:
        finding("R2_dash_eps", "HIGH", "SILENT-WRONG",
                f"Dashboard EPS ({fmt_val(dash_eps)}) != E4 EPS ({fmt_val(e4_eps)})",
                {"dash": dash_eps, "e4": e4_eps})
    else:
        finding("R2_dash_eps", "info", "LOUD-OK",
                f"Dashboard EPS matches E4 ({fmt_val(e4_eps)})", {})
else:
    finding("R2_dash_eps", "LOW", "MISLEADING",
            f"EPS type mismatch: dash={type(dash_eps).__name__}={dash_eps}, e4={type(e4_eps).__name__}={e4_eps}",
            {"dash": str(dash_eps), "e4": str(e4_eps)})

# ── R3: Henkel Summary vs E3 consistency ──
print("\n▸ R3: Henkel Summary vs E3 interest")
hs_interest = bl.get('hs_interest_eur_y1')
hs_finres = bl.get('hs_net_finres_y1')
e3_finres = bl.get('e3_net_finres_y1')

if isinstance(hs_finres, (int,float)) and isinstance(e3_finres, (int,float)):
    if abs(hs_finres - e3_finres) > 0.01:
        finding("R3_hs_e3_finres", "MEDIUM", "MISLEADING",
                f"Henkel Summary finres ({fmt_val(hs_finres)}) != E3 finres ({fmt_val(e3_finres)})",
                {"hs": hs_finres, "e3": e3_finres})
    else:
        finding("R3_hs_e3_finres", "info", "LOUD-OK",
                f"Henkel Summary finres matches E3 ({fmt_val(e3_finres)})", {})
else:
    finding("R3_hs_e3_finres", "LOW", "MISLEADING",
            f"Finres type issue: hs={hs_finres}, e3={e3_finres}",
            {"hs": str(hs_finres), "e3": str(e3_finres)})

# ── R4: AT verdict string matches count ──
print("\n▸ R4: AT verdict consistency")
at_fail = bl.get('at_failing')
at_verdict = bl.get('at_verdict')
if at_fail == 0 and isinstance(at_verdict, str) and "pass" in at_verdict.lower():
    finding("R4_at_consistent", "info", "LOUD-OK",
            f"AT verdict consistent: {at_fail} failures, verdict='{str(at_verdict)[:50]}'", {})
elif at_fail == 0 and isinstance(at_verdict, str) and "pass" not in at_verdict.lower():
    finding("R4_at_inconsistent", "HIGH", "SILENT-WRONG",
            f"AT says 0 failures but verdict doesn't say pass: '{str(at_verdict)[:80]}'",
            {"failing": at_fail, "verdict": at_verdict})
elif at_fail is not None and at_fail > 0 and isinstance(at_verdict, str) and "pass" in at_verdict.lower():
    finding("R4_at_false_pass", "HIGH", "SILENT-WRONG",
            f"AT has {at_fail} failures but verdict says pass",
            {"failing": at_fail, "verdict": at_verdict})
else:
    finding("R4_at_consistent", "info", "LOUD-OK",
            f"AT verdict: {at_fail} failures, verdict='{str(at_verdict)[:50]}'", {})

# ── R5: Stress scenario changes outputs meaningfully ──
print("\n▸ R5: Stress scenario impact")
r_stress = run("R5_stress", {"Dashboard!B9": "Stress"})
diffs = compare(bl, r_stress, tol=0.01)
if len(diffs) < 3:
    finding("R5_stress_impact", "MEDIUM", "MISLEADING",
            f"Stress scenario only changes {len(diffs)} outputs (expected broad impact)",
            {"diffs": [(k, fmt_val(bv), fmt_val(tv)) for k,bv,tv,_ in diffs[:5]]})
else:
    finding("R5_stress_impact", "info", "LOUD-OK",
            f"Stress scenario changes {len(diffs)} outputs (healthy breadth)", {})

# ── R6: Funding-only toggle ──
print("\n▸ R6: Funding-only toggle effect")
r_fundonly = run("R6_funding_only", {"1. Deal Inputs!B65": "Y"})
eps_fo = r_fundonly.get('e4_eps_y1')
eps_bl = bl.get('e4_eps_y1')
if isinstance(eps_fo, (int,float)) and isinstance(eps_bl, (int,float)):
    if abs(eps_fo - eps_bl) < 0.001:
        finding("R6_funding_only", "MEDIUM", "MISLEADING",
                f"Funding-only toggle doesn't change EPS ({fmt_val(eps_bl)})",
                {"bl_eps": eps_bl, "fo_eps": eps_fo})
    else:
        finding("R6_funding_only", "info", "LOUD-OK",
                f"Funding-only toggle changes EPS: {fmt_val(eps_bl)} → {fmt_val(eps_fo)}", {})
else:
    finding("R6_funding_only", "LOW", "MISLEADING",
            f"EPS non-numeric: bl={eps_bl}, fo={eps_fo}", {})

# ── R7: Check balance chain: open → interest → close ──
print("\n▸ R7: Balance chain consistency")
open_bal = bl.get('e3_open_bal_y1')
close_bal = bl.get('e3_close_bal_y1')
interest = bl.get('e3_interest_y1')
amount = bl.get('e3_amount_raised')

if all(isinstance(v, (int,float)) for v in [open_bal, close_bal, interest, amount]):
    if close_bal > open_bal * 1.5:
        finding("R7_bal_chain", "MEDIUM", "MISLEADING",
                f"Close bal ({fmt_val(close_bal)}) > 1.5x open ({fmt_val(open_bal)})",
                {"open": open_bal, "close": close_bal})
    else:
        finding("R7_bal_chain", "info", "LOUD-OK",
                f"Balance chain looks reasonable: open={fmt_val(open_bal)}, close={fmt_val(close_bal)}", {})
else:
    finding("R7_bal_chain", "LOW", "MISLEADING",
            f"Non-numeric balance: open={open_bal}, close={close_bal}", {})

# ═══ SUMMARY ═══
print("\n" + "=" * 70)
print("BLOCK 6 SUMMARY")
print("=" * 70)
for cls in ["SILENT-WRONG", "CRASH", "MISLEADING", "FALSE-ALARM", "LOUD-OK"]:
    items = [f for f in FINDINGS if f['class'] == cls]
    if items:
        icon = {"SILENT-WRONG": "🔴", "CRASH": "⚪", "MISLEADING": "🟡",
                "FALSE-ALARM": "🟠", "LOUD-OK": "🟢"}[cls]
        print(f"\n  {icon} {cls} ({len(items)}):")
        for f in items:
            print(f"    {f['test']}: {f['desc'][:100]}")

with open(STRESS_DIR / "block6_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
