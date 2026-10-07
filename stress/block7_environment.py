#!/usr/bin/env python3 -I
"""
Block 7 — Performance & Environment.
Tests reproducibility, recalc consistency, and environmental edge cases.
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
print("BLOCK 7 — PERFORMANCE & ENVIRONMENT")
print("=" * 70)

# ── E1: Reproducibility — run baseline twice ──
print("\n▸ E1: Reproducibility (baseline × 2)")
bl1 = run("E1_baseline_1", {})
bl2 = run("E1_baseline_2", {})
diffs = compare(bl1, bl2, tol=0.0)
if diffs:
    finding("E1_reproducibility", "HIGH", "SILENT-WRONG",
            f"Baseline not reproducible: {len(diffs)} diffs",
            {"diffs": [(k, fmt_val(bv), fmt_val(tv)) for k,bv,tv,_ in diffs[:5]]})
else:
    finding("E1_reproducibility", "info", "LOUD-OK",
            "Baseline is perfectly reproducible (2 runs identical)", {})

# ── E2: Identity test — write same values back ──
print("\n▸ E2: Identity (write baseline values back)")
r_identity = run("E2_identity", {
    "1. Deal Inputs!B9": 1000,
    "1. Deal Inputs!B42": 0.266,
    "1. Deal Inputs!B44": 438,
})
diffs = compare(bl1, r_identity, tol=0.001)
if diffs:
    num_diffs = [d for d in diffs if isinstance(d[1], (int,float)) and isinstance(d[2], (int,float))]
    if num_diffs:
        finding("E2_identity", "MEDIUM", "MISLEADING",
                f"Writing same values back changes {len(num_diffs)} outputs",
                {"diffs": [(k, fmt_val(bv), fmt_val(tv)) for k,bv,tv,_ in num_diffs[:5]]})
    else:
        finding("E2_identity", "info", "LOUD-OK",
                "Identity: only type differences (format changes)", {})
else:
    finding("E2_identity", "info", "LOUD-OK",
            "Identity test passes (same inputs → same outputs)", {})

# ── E3: Reversibility — change and change back ──
print("\n▸ E3: Reversibility (change PP then revert)")
r_changed = run("E3_change_pp", {"1. Deal Inputs!B9": 2000})
r_reverted = run("E3_revert_pp", {"1. Deal Inputs!B9": 1000})
diffs = compare(bl1, r_reverted, tol=0.001)
if diffs:
    num_diffs = [d for d in diffs if isinstance(d[1], (int,float)) and isinstance(d[2], (int,float))]
    if num_diffs:
        finding("E3_revert", "MEDIUM", "MISLEADING",
                f"Reverting PP doesn't restore outputs ({len(num_diffs)} diffs)",
                {"diffs": [(k, fmt_val(bv), fmt_val(tv)) for k,bv,tv,_ in num_diffs[:5]]})
    else:
        finding("E3_revert", "info", "LOUD-OK",
                "Revert: only type differences", {})
else:
    finding("E3_revert", "info", "LOUD-OK",
            "Reversibility: change PP→2000→1000 gives original results", {})

# ── E4: Many overrides at once ──
print("\n▸ E4: Many simultaneous overrides")
r_many = run("E4_many_overrides", {
    "1. Deal Inputs!B9": 1500,
    "1. Deal Inputs!B42": 0.30,
    "1. Deal Inputs!B44": 500,
    "1. Deal Inputs!B40": 6,
    "3. Scenario & Mix!C8": 0.80,
    "3. Scenario & Mix!C9": 0.20,
})
if r_many.get('_error'):
    finding("E4_many", "MEDIUM", "CRASH",
            f"Many overrides failed: {r_many.get('_error')}",
            {"error": r_many.get('_error')})
elif r_many.get('at_failing', 99) == 0:
    finding("E4_many", "info", "LOUD-OK",
            f"Many overrides: AT passes, rate={fmt_val(r_many.get('e3_allin_y1'))}",
            {"rate": r_many.get('e3_allin_y1'), "eps": r_many.get('e4_eps_y1')})
else:
    finding("E4_many", "info", "LOUD-OK",
            f"Many overrides: AT catches ({r_many.get('at_failing')} failures)", {})

# ═══ SUMMARY ═══
print("\n" + "=" * 70)
print("BLOCK 7 SUMMARY")
print("=" * 70)
for cls in ["SILENT-WRONG", "CRASH", "MISLEADING", "FALSE-ALARM", "LOUD-OK"]:
    items = [f for f in FINDINGS if f['class'] == cls]
    if items:
        icon = {"SILENT-WRONG": "🔴", "CRASH": "⚪", "MISLEADING": "🟡",
                "FALSE-ALARM": "🟠", "LOUD-OK": "🟢"}[cls]
        print(f"\n  {icon} {cls} ({len(items)}):")
        for f in items:
            print(f"    {f['test']}: {f['desc'][:100]}")

with open(STRESS_DIR / "block7_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
