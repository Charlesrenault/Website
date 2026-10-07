#!/usr/bin/env python3 -I
"""
Block 3 — Combinatorial Lever Flips.
Tests discrete lever combinations for dead switches, leaking controls, and AT failures.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from harness import run, run_baseline, compare, fmt_val, STRESS_DIR
from datetime import datetime
import json, itertools

FINDINGS = []

def finding(test_id, severity, classification, desc, evidence):
    f = {"test": test_id, "severity": severity, "class": classification,
         "desc": desc, "evidence": evidence}
    FINDINGS.append(f)
    marker = {"SILENT-WRONG": "🔴", "MISLEADING": "🟡", "LOUD-OK": "🟢",
              "CRASH": "⚪", "FALSE-ALARM": "🟠"}.get(classification, "⚫")
    print(f"  {marker} [{classification}] {desc}")

print("=" * 70)
print("BLOCK 3 — COMBINATORIAL LEVER FLIPS")
print("=" * 70)

bl = run_baseline()

# Define the discrete levers
SCENARIOS = {
    "Base": {},
    "Downside": {"Dashboard!B9": "Downside"},
    "Stress": {"Dashboard!B9": "Stress"},
}

FCF_MODES = {
    "amortise": {"1. Deal Inputs!B35": "pays down debt (amortise)"},
    "earns": {"1. Deal Inputs!B35": "earns income per currency"},
}

CASH_MODES = {
    "reduces": {"1. Deal Inputs!B30": "reduces financing need (no income)"},
    "held": {"1. Deal Inputs!B30": "held as cash (earns income)"},
}

REFI_MODES = {
    "excl": {"1. Deal Inputs!B36": "exclude (show ladder only)"},
    "incl": {"1. Deal Inputs!B36": "include in horizon"},
}

SALE_MODES = {
    "none": {},
    "uniform_50": {"1. Deal Inputs!B57": 0.5, "1. Deal Inputs!B58": 3},
    "targeted": {
        "3. Scenario & Mix!A86": "EUR",
        "3. Scenario & Mix!B86": 0.5,
        "3. Scenario & Mix!C86": 3,
    },
}

# Run a subset (full factorial would be 3×2×2×2×3=72 runs)
# Focus on key combos that test interactions
combos = list(itertools.product(
    SCENARIOS.items(),
    FCF_MODES.items(),
    CASH_MODES.items(),
    SALE_MODES.items(),
))

dead_switches = []
at_failures = []
results = {}

print(f"\nRunning {len(combos)} combinations...")
for (sc_name, sc_ov), (fcf_name, fcf_ov), (cash_name, cash_ov), (sale_name, sale_ov) in combos:
    combo_name = f"{sc_name}_{fcf_name}_{cash_name}_{sale_name}"
    overrides = {}
    overrides.update(sc_ov)
    overrides.update(fcf_ov)
    overrides.update(cash_ov)
    overrides.update(sale_ov)

    r = run(f"L3_{combo_name}", overrides)
    results[combo_name] = r

    at_fail = r.get('at_failing', 99)
    ready = r.get('model_ready')
    rate = r.get('e3_allin_y1')
    interest = r.get('e3_interest_y1')

    # Check for AT failures
    if at_fail > 0:
        at_failures.append((combo_name, at_fail, r.get('_at_failing_list', [])))

    # Check invariants
    if isinstance(interest, (int, float)) and isinstance(r.get('e3_amount_raised'), (int, float)):
        if interest > r['e3_amount_raised'] and r['e3_amount_raised'] > 0:
            finding(f"L3_{combo_name}", "HIGH", "SILENT-WRONG",
                    f"Interest > amount raised",
                    {"interest": interest, "amount": r['e3_amount_raised']})

# Check for dead switches (lever that changes nothing)
print("\n▸ Checking for dead switches...")

# Test: Does changing scenario change the rate?
base_base = results.get("Base_earns_reduces_none", {})
down_earns = results.get("Downside_earns_reduces_none", {})
stress_earns = results.get("Stress_earns_reduces_none", {})

if base_base and down_earns:
    rate_changes = not (base_base.get('e3_allin_y1') == down_earns.get('e3_allin_y1'))
    eps_changes = not (base_base.get('e4_eps_y1') == down_earns.get('e4_eps_y1'))
    if not rate_changes and not eps_changes:
        dead_switches.append("Scenario (Base→Downside)")
        finding("L3_dead_scenario", "HIGH", "SILENT-WRONG",
                "Scenario selector is a DEAD SWITCH — Base→Downside changes nothing",
                {"base_rate": fmt_val(base_base.get('e3_allin_y1')),
                 "down_rate": fmt_val(down_earns.get('e3_allin_y1'))})
    elif not rate_changes:
        finding("L3_scenario_rate", "info", "LOUD-OK",
                f"Scenario changes EPS ({fmt_val(base_base.get('e4_eps_y1'))} → "
                f"{fmt_val(down_earns.get('e4_eps_y1'))}) but not rate (expected — rate is market-driven)",
                {})

# Test: FCF mode changes interest?
base_amort = results.get("Base_amortise_reduces_none", {})
base_earns_r = results.get("Base_earns_reduces_none", {})
if base_amort and base_earns_r:
    int_diff = base_amort.get('e3_interest_y1') != base_earns_r.get('e3_interest_y1')
    bal_diff = base_amort.get('e3_close_bal_y1') != base_earns_r.get('e3_close_bal_y1')
    if not int_diff and not bal_diff:
        dead_switches.append("FCF mode (amortise vs earns)")
        # But this might be expected if there's no FCF in Y1
        finding("L3_dead_fcf", "LOW", "MISLEADING",
                "FCF mode doesn't change Y1 (may be OK if no FCF in Y1)",
                {"amort_int": fmt_val(base_amort.get('e3_interest_y1')),
                 "earns_int": fmt_val(base_earns_r.get('e3_interest_y1'))})

# Test: Cash treatment changes output?
earns_reduces = results.get("Base_earns_reduces_none", {})
earns_held = results.get("Base_earns_held_none", {})
if earns_reduces and earns_held:
    finres_diff = earns_reduces.get('e3_net_finres_y1') != earns_held.get('e3_net_finres_y1')
    if not finres_diff:
        # With cash=0 in baseline, this is expected
        finding("L3_cash_mode", "LOW", "MISLEADING",
                "Cash treatment makes no difference (cash=0 in baseline — test with cash>0)",
                {"reduces_finres": fmt_val(earns_reduces.get('e3_net_finres_y1')),
                 "held_finres": fmt_val(earns_held.get('e3_net_finres_y1'))})

# AT failures summary
print(f"\n▸ AT failures across {len(combos)} combinations: {len(at_failures)}")
for combo, fails, details in at_failures:
    print(f"    {combo}: {fails} failures — {str(details)[:100]}")

# ═══ SUMMARY ═══
print("\n" + "=" * 70)
print("BLOCK 3 SUMMARY")
print("=" * 70)
print(f"  Combinations tested: {len(combos)}")
print(f"  AT failures: {len(at_failures)}")
print(f"  Dead switches found: {dead_switches if dead_switches else 'None'}")

for cls in ["SILENT-WRONG", "CRASH", "MISLEADING", "FALSE-ALARM", "LOUD-OK"]:
    items = [f for f in FINDINGS if f['class'] == cls]
    if items:
        icon = {"SILENT-WRONG": "🔴", "CRASH": "⚪", "MISLEADING": "🟡",
                "FALSE-ALARM": "🟠", "LOUD-OK": "🟢"}[cls]
        print(f"  {icon} {cls} ({len(items)}):")
        for f in items:
            print(f"    {f['test']}: {f['desc'][:100]}")

with open(STRESS_DIR / "block3_findings.json", "w") as fp:
    json.dump(FINDINGS, fp, indent=2, default=str)
