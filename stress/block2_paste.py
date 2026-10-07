#!/usr/bin/env python3 -I
"""
Block 2 — Data-Paste Hazards.
Tests whether pasting wrong-shaped or wrong-typed data into key ranges
produces silent errors, or whether the model catches them.
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
print("BLOCK 2 — DATA-PASTE HAZARDS")
print("=" * 70)

bl = run_baseline()

# ── P1: Swap EUR and USD rows in the mix table ──
print("\n▸ P1: Swap EUR/USD rows in mix table")
r_swap = run("P1_swap_mix", {
    "3. Scenario & Mix!A8": "USD",
    "3. Scenario & Mix!A9": "EUR",
    "3. Scenario & Mix!C8": 0.30,
    "3. Scenario & Mix!C9": 0.70,
})
diffs = compare(bl, r_swap, tol=0.001)
if r_swap.get('at_failing', 99) == 0 and diffs:
    finding("P1_swap_mix", "MEDIUM", "MISLEADING",
            f"Swapping EUR/USD rows passes AT but changes outputs",
            {"diffs": [(k, fmt_val(bv), fmt_val(tv)) for k,bv,tv,_ in diffs[:5]],
             "at": r_swap.get('at_failing')})
elif r_swap.get('at_failing', 0) > 0:
    finding("P1_swap_mix", "info", "LOUD-OK",
            f"Swap EUR/USD rows: AT catches ({r_swap.get('at_failing')} failures)", {})
else:
    finding("P1_swap_mix", "info", "LOUD-OK",
            f"Swap EUR/USD rows: no significant output change", {})

# ── P2: Paste text where number expected (spread cells) ──
print("\n▸ P2: Text in numeric fields")
text_cases = [
    ("P2_text_pp", {"1. Deal Inputs!B9": "one billion"}, "PP=text"),
    ("P2_text_tax", {"1. Deal Inputs!B42": "twenty six"}, "tax=text"),
    ("P2_text_mix", {"3. Scenario & Mix!C8": "seventy"}, "mix=text"),
]
for name, ov, desc in text_cases:
    r = run(name, ov)
    ready = r.get('model_ready')
    at_fail = r.get('at_failing', 99)
    if ready and at_fail == 0:
        finding(name, "HIGH", "SILENT-WRONG",
                f"{desc}: model ready, AT passes",
                {"rate": fmt_val(r.get('e3_allin_y1')),
                 "interest": fmt_val(r.get('e3_interest_y1'))})
    elif not ready or at_fail > 0:
        finding(name, "info", "LOUD-OK",
                f"{desc}: model refuses or AT catches (ready={ready}, at={at_fail})", {})
    else:
        finding(name, "MEDIUM", "CRASH",
                f"{desc}: unexpected state",
                {"ready": ready, "at": at_fail})

# ── P3: Duplicate currency in mix ──
print("\n▸ P3: Duplicate currency in mix table")
r_dup = run("P3_dup_ccy", {
    "3. Scenario & Mix!A8": "EUR",
    "3. Scenario & Mix!A9": "EUR",
    "3. Scenario & Mix!C8": 0.50,
    "3. Scenario & Mix!C9": 0.50,
})
diffs = compare(bl, r_dup, tol=0.001)
if r_dup.get('at_failing', 99) == 0:
    finding("P3_dup_ccy", "HIGH", "SILENT-WRONG",
            f"Duplicate EUR in mix: AT passes, diffs={len(diffs)}",
            {"rate": fmt_val(r_dup.get('e3_allin_y1')),
             "bl_rate": fmt_val(bl.get('e3_allin_y1')),
             "at": r_dup.get('at_failing')})
else:
    finding("P3_dup_ccy", "info", "LOUD-OK",
            f"Duplicate EUR: AT catches ({r_dup.get('at_failing')} failures)", {})

# ── P4: Mix sums to 0% ──
print("\n▸ P4: Mix sums to 0%")
r_mix0 = run("P4_mix_zero", {
    "3. Scenario & Mix!C8": 0,
    "3. Scenario & Mix!C9": 0,
    "3. Scenario & Mix!C10": 0,
    "3. Scenario & Mix!C11": 0,
})
if r_mix0.get('model_ready') and r_mix0.get('at_failing', 99) == 0:
    finding("P4_mix_zero", "HIGH", "SILENT-WRONG",
            f"Mix=0%: model ready, AT passes",
            {"rate": fmt_val(r_mix0.get('e3_allin_y1')),
             "amount": fmt_val(r_mix0.get('e3_amount_raised'))})
elif r_mix0.get('at_failing', 0) > 0:
    finding("P4_mix_zero", "info", "LOUD-OK",
            f"Mix=0%: AT catches ({r_mix0.get('at_failing')} failures)", {})
else:
    finding("P4_mix_zero", "MEDIUM", "MISLEADING",
            f"Mix=0%: model not ready but no explicit error",
            {"ready": r_mix0.get('model_ready')})

# ── P5: Negative values in mix ──
print("\n▸ P5: Negative mix percentages")
r_negmix = run("P5_neg_mix", {
    "3. Scenario & Mix!C8": -0.30,
    "3. Scenario & Mix!C9": 1.30,
})
if r_negmix.get('at_failing', 99) == 0:
    finding("P5_neg_mix", "MEDIUM", "SILENT-WRONG",
            f"Negative mix (-30% EUR, 130% USD): AT passes",
            {"rate": fmt_val(r_negmix.get('e3_allin_y1')),
             "interest": fmt_val(r_negmix.get('e3_interest_y1'))})
else:
    finding("P5_neg_mix", "info", "LOUD-OK",
            f"Negative mix: AT catches ({r_negmix.get('at_failing')} failures)", {})

# ── P6: Wrong date format (number instead of date) ──
print("\n▸ P6: Numeric pasted as date")
r_datenum = run("P6_date_as_num", {
    "1. Deal Inputs!B19": 45000,  # Excel serial for ~2023
    "1. Deal Inputs!B20": 45100,
    "1. Deal Inputs!B21": 45100,
})
if r_datenum.get('at_failing', 99) == 0:
    finding("P6_date_num", "MEDIUM", "MISLEADING",
            f"Date as serial number: AT passes (Excel may handle this correctly)",
            {"rate": fmt_val(r_datenum.get('e3_allin_y1'))})
else:
    finding("P6_date_num", "info", "LOUD-OK",
            f"Date serial: AT catches ({r_datenum.get('at_failing')} failures)", {})

# ── P7: Sale table with mismatched currencies ──
print("\n▸ P7: Sale table currency not in mix")
r_bad_sale = run("P7_sale_ccy_mismatch", {
    "3. Scenario & Mix!A86": "GBP",  # GBP not in mix
    "3. Scenario & Mix!B86": 0.5,
    "3. Scenario & Mix!C86": 3,
})
if r_bad_sale.get('at_failing', 99) == 0:
    shed = r_bad_sale.get('hs_interest_shed')
    finding("P7_sale_mismatch", "MEDIUM", "SILENT-WRONG",
            f"Sale of GBP (not in mix): AT passes, shed={fmt_val(shed)}",
            {"shed": shed, "post_sale_int": fmt_val(r_bad_sale.get('hs_post_sale_interest'))})
else:
    finding("P7_sale_mismatch", "info", "LOUD-OK",
            f"Sale ccy mismatch: AT catches ({r_bad_sale.get('at_failing')} failures)", {})

# ── P8: Extremely long text in a text field ──
print("\n▸ P8: Very long text injection")
r_long = run("P8_long_text", {
    "Dashboard!B9": "A" * 1000,
})
if r_long.get('model_ready') and r_long.get('at_failing', 99) == 0:
    finding("P8_long_text", "LOW", "SILENT-WRONG",
            f"1000-char text in scenario selector: model runs",
            {"ready": r_long.get('model_ready')})
else:
    finding("P8_long_text", "info", "LOUD-OK",
            f"Long text: model handles it (ready={r_long.get('model_ready')}, at={r_long.get('at_failing')})", {})

# ── P9: Formula injection ──
print("\n▸ P9: Formula injection in text field")
r_formula = run("P9_formula_inject", {
    "Dashboard!B9": "=1+1",
})
if r_formula.get('_error'):
    finding("P9_formula_inject", "info", "CRASH",
            f"Formula injection crashed: {r_formula.get('_error')}", {})
else:
    finding("P9_formula_inject", "info", "LOUD-OK",
            f"Formula injection handled (ready={r_formula.get('model_ready')}, at={r_formula.get('at_failing')})", {})

# ── P10: All currencies set to same ──
print("\n▸ P10: All currencies identical")
r_alleur = run("P10_all_eur", {
    "3. Scenario & Mix!A8": "EUR",
    "3. Scenario & Mix!A9": "EUR",
    "3. Scenario & Mix!A10": "EUR",
    "3. Scenario & Mix!A11": "EUR",
    "3. Scenario & Mix!C8": 0.25,
    "3. Scenario & Mix!C9": 0.25,
    "3. Scenario & Mix!C10": 0.25,
    "3. Scenario & Mix!C11": 0.25,
})
if r_alleur.get('at_failing', 99) == 0:
    finding("P10_all_eur", "MEDIUM", "SILENT-WRONG",
            f"All 4 rows = EUR: AT passes",
            {"rate": fmt_val(r_alleur.get('e3_allin_y1')),
             "interest": fmt_val(r_alleur.get('e3_interest_y1'))})
else:
    finding("P10_all_eur", "info", "LOUD-OK",
            f"All EUR: AT catches ({r_alleur.get('at_failing')} failures)", {})

# ═══ SUMMARY ═══
print("\n" + "=" * 70)
print("BLOCK 2 SUMMARY")
print("=" * 70)
for cls in ["SILENT-WRONG", "CRASH", "MISLEADING", "FALSE-ALARM", "LOUD-OK"]:
    items = [f for f in FINDINGS if f['class'] == cls]
    if items:
        icon = {"SILENT-WRONG": "🔴", "CRASH": "⚪", "MISLEADING": "🟡",
                "FALSE-ALARM": "🟠", "LOUD-OK": "🟢"}[cls]
        print(f"\n  {icon} {cls} ({len(items)}):")
        for f in items:
            print(f"    {f['test']}: {f['desc'][:100]}")

with open(STRESS_DIR / "block2_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
