#!/usr/bin/env python3 -I
"""
Block 1 — Boundary & Garbage Inputs: push each input to extremes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import run, run_baseline, compare, fmt_val, STRESS_DIR
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

print("=" * 70)
print("BLOCK 1 — BOUNDARY & GARBAGE INPUTS")
print("=" * 70)

bl = run_baseline()

# ── PP edge cases ──
print("\n▸ B1.1: Purchase Price edge cases")
pp_cases = [
    ("PP_zero", 0, "PP=0"),
    ("PP_negative", -500, "PP=-500"),
    ("PP_tiny", 0.001, "PP=0.001mm"),
    ("PP_huge", 1000000, "PP=1,000,000mm"),
    ("PP_text", "one billion", "PP=text"),
    ("PP_blank", None, "PP=blank"),
]
for name, val, desc in pp_cases:
    r = run(f"B1_{name}", {"1. Deal Inputs!B9": val})
    ready = r.get('model_ready')
    at_fail = r.get('at_failing', 99)
    if val in (0, None, "one billion") and ready:
        finding(f"B1_{name}", "HIGH", "SILENT-WRONG",
                f"{desc}: model says READY (should refuse)",
                {"ready": ready, "at": at_fail, "int": fmt_val(r.get('e3_interest_y1'))})
    elif val in (0, None, "one billion") and not ready:
        finding(f"B1_{name}", "info", "LOUD-OK",
                f"{desc}: model correctly refuses",
                {"ready": ready, "at": at_fail})
    elif val == -500:
        if ready:
            finding(f"B1_{name}", "HIGH", "SILENT-WRONG",
                    f"{desc}: negative PP accepted (interest={fmt_val(r.get('e3_interest_y1'))})",
                    {"interest": r.get('e3_interest_y1'), "at": at_fail})
        else:
            finding(f"B1_{name}", "info", "LOUD-OK", f"{desc}: refused", {})
    else:
        finding(f"B1_{name}", "info", "LOUD-OK",
                f"{desc}: ready={ready}, at_fail={at_fail}",
                {"interest": fmt_val(r.get('e3_interest_y1'))})

# ── Tax rate: percent-vs-fraction slip ──
print("\n▸ B1.2: Tax rate percent-vs-fraction slip")
r_26pct = run("B1_tax_26pct", {"1. Deal Inputs!B42": 26.6})  # 26.6 instead of 0.266
if r_26pct.get('model_ready') and r_26pct.get('at_failing', 99) == 0:
    finding("B1_tax_slip", "HIGH", "SILENT-WRONG",
            f"Tax=26.6 (should be 0.266): AT passes, EPS={fmt_val(r_26pct.get('e4_eps_y1'))}",
            {"eps": fmt_val(r_26pct.get('e4_eps_y1')),
             "bl_eps": fmt_val(bl['e4_eps_y1']),
             "note": "2560% tax rate accepted silently"})
elif r_26pct.get('at_failing', 0) > 0:
    finding("B1_tax_slip", "info", "LOUD-OK",
            f"Tax=26.6: AT catches it ({r_26pct.get('at_failing')} failures)", {})
else:
    finding("B1_tax_slip", "MEDIUM", "CRASH",
            f"Tax=26.6: model not ready",
            {"ready": r_26pct.get('model_ready')})

# Tax >100%
r_tax_high = run("B1_tax_101pct", {"1. Deal Inputs!B42": 1.01})
if r_tax_high.get('at_failing', 99) == 0:
    finding("B1_tax_101", "MEDIUM", "SILENT-WRONG",
            f"Tax=101%: AT passes, EPS={fmt_val(r_tax_high.get('e4_eps_y1'))}",
            {"eps": r_tax_high.get('e4_eps_y1')})
else:
    finding("B1_tax_101", "info", "LOUD-OK",
            f"Tax=101%: AT catches ({r_tax_high.get('at_failing')} failures)", {})

# Negative tax
r_tax_neg = run("B1_tax_neg", {"1. Deal Inputs!B42": -0.1})
if r_tax_neg.get('at_failing', 99) == 0:
    finding("B1_tax_neg", "MEDIUM", "SILENT-WRONG",
            f"Tax=-10%: AT passes (negative tax → income is a subsidy?)",
            {"eps": fmt_val(r_tax_neg.get('e4_eps_y1'))})
else:
    finding("B1_tax_neg", "info", "LOUD-OK",
            f"Tax=-10%: AT catches it", {})

# ── Shares outstanding ──
print("\n▸ B1.3: Shares outstanding edge cases")
r_shares_0 = run("B1_shares_0", {"1. Deal Inputs!B44": 0})
r_shares_neg = run("B1_shares_neg", {"1. Deal Inputs!B44": -100})
r_shares_blank = run("B1_shares_blank", {"1. Deal Inputs!B44": None})

for name, r, expected in [
    ("shares=0", r_shares_0, "should refuse or show n/a for EPS"),
    ("shares=-100", r_shares_neg, "should refuse negative shares"),
    ("shares=blank", r_shares_blank, "should show n/a for EPS"),
]:
    eps = r.get('e4_eps_y1')
    if isinstance(eps, (int, float)) and name == "shares=0":
        finding(f"B1_{name}", "HIGH", "CRASH",
                f"{name}: EPS={fmt_val(eps)} — division by zero not caught",
                {"eps": eps, "at": r.get('at_failing')})
    elif isinstance(eps, str) and ("n/a" in eps.lower() or "—" in eps):
        finding(f"B1_{name}", "info", "LOUD-OK", f"{name}: EPS={eps}", {})
    elif eps is None:
        finding(f"B1_{name}", "info", "LOUD-OK", f"{name}: EPS=None (blank)", {})
    else:
        finding(f"B1_{name}", "MEDIUM", "SILENT-WRONG" if r.get('at_failing',99)==0 else "LOUD-OK",
                f"{name}: EPS={fmt_val(eps)}", {"at": r.get('at_failing')})

# ── Horizon length ──
print("\n▸ B1.4: Horizon length edge cases")
for hl, name in [(0, "H0"), (1, "H1"), (9, "H9")]:
    r = run(f"B1_{name}", {"1. Deal Inputs!B40": hl})
    finding(f"B1_{name}", "MEDIUM" if r.get('at_failing',99)==0 and hl in (0,9) else "info",
            "SILENT-WRONG" if r.get('at_failing',99)==0 and hl in (0,9) else "LOUD-OK",
            f"Horizon={hl}: AT fail={r.get('at_failing')}, rate={fmt_val(r.get('e3_allin_y1'))}",
            {"at": r.get('at_failing'), "int": fmt_val(r.get('e3_interest_y1'))})

# ── Closing before signing ──
print("\n▸ B1.5: Closing before signing")
r_early = run("B1_close_before_sign", {
    "1. Deal Inputs!B19": datetime(2026, 9, 30),  # signing
    "1. Deal Inputs!B20": datetime(2026, 5, 1),   # closing before signing
    "1. Deal Inputs!B21": datetime(2026, 5, 1),
})
finding("B1_early_close",
        "MEDIUM" if r_early.get('at_failing',99)==0 else "info",
        "SILENT-WRONG" if r_early.get('at_failing',99)==0 else "LOUD-OK",
        f"Close before signing: AT fail={r_early.get('at_failing')}",
        {"at": r_early.get('at_failing'), "verdict": str(r_early.get('at_verdict'))[:100]})

# ── Mix edge cases ──
print("\n▸ B1.6: Mix edge cases")
# Mix = 99%
r_mix99 = run("B1_mix_99pct", {
    "3. Scenario & Mix!C8": 0.99,  # Only EUR at 99%
    "3. Scenario & Mix!C9": 0,
})
finding("B1_mix99",
        "MEDIUM" if r_mix99.get('at_failing',99)==0 else "info",
        "SILENT-WRONG" if r_mix99.get('at_failing',99)==0 else "LOUD-OK",
        f"Mix=99%: AT fail={r_mix99.get('at_failing')}",
        {"verdict": str(r_mix99.get('at_verdict'))[:100]})

# Mix = 101%
r_mix101 = run("B1_mix_101pct", {
    "3. Scenario & Mix!C8": 0.70,
    "3. Scenario & Mix!C9": 0.31,  # EUR+USD = 101%
})
finding("B1_mix101",
        "MEDIUM" if r_mix101.get('at_failing',99)==0 else "info",
        "SILENT-WRONG" if r_mix101.get('at_failing',99)==0 else "LOUD-OK",
        f"Mix=101%: AT fail={r_mix101.get('at_failing')}",
        {"verdict": str(r_mix101.get('at_verdict'))[:100]})

# ── Acquired cash > PP ──
print("\n▸ B1.7: Acquired cash > PP")
r_cashbig = run("B1_cash_gt_pp", {
    "1. Deal Inputs!B33": 1500,  # Cash > PP=1000
    "1. Deal Inputs!B30": "reduces financing need (no income)",
})
amt_raised = r_cashbig.get('e3_amount_raised')
finding("B1_cash_gt_pp",
        "MEDIUM" if (isinstance(amt_raised, (int,float)) and amt_raised < 0) else "info",
        "SILENT-WRONG" if (isinstance(amt_raised, (int,float)) and amt_raised < 0) else "LOUD-OK",
        f"Cash=1500>PP=1000: amount_raised={fmt_val(amt_raised)}",
        {"amt": amt_raised, "int": fmt_val(r_cashbig.get('e3_interest_y1')),
         "at": r_cashbig.get('at_failing')})

# ═══ SUMMARY ═══
print("\n" + "=" * 70)
print("BLOCK 1 SUMMARY")
print("=" * 70)
for cls in ["SILENT-WRONG", "CRASH", "MISLEADING", "FALSE-ALARM", "LOUD-OK"]:
    items = [f for f in FINDINGS if f['class'] == cls]
    if items:
        icon = {"SILENT-WRONG": "🔴", "CRASH": "⚪", "MISLEADING": "🟡",
                "FALSE-ALARM": "🟠", "LOUD-OK": "🟢"}[cls]
        print(f"\n  {icon} {cls} ({len(items)}):")
        for f in items:
            print(f"    {f['test']}: {f['desc'][:100]}")

with open(STRESS_DIR / "block1_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
