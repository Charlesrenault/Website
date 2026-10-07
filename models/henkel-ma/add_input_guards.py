"""Add input-boundary validation checks to the ✓ Acceptance Test tab.

These are pure guardrails — they don't touch any engine formula.
They make the AT verdict flip ❌ when garbage inputs go in.
"""

import openpyxl
from copy import copy

SRC = "/mnt/user-data/outputs/Henkel_MA_Financing_Model_teilverkauf_ccy.xlsx"
DST = SRC

wb = openpyxl.load_workbook(SRC)
ws = wb["✓ Acceptance Test"]

# ── placement ───────────────────────────────────────────────────────
# Existing checks end at row 75.  Rows 77-87 are documentation text.
# Verdict formula at B5 counts B8:B120, so rows 89-99 are within range.
# ────────────────────────────────────────────────────────────────────

START = 89

# section header
ws.cell(START, 1, "⑬ INPUT BOUNDS (stress-test guardrails)")

checks = [
    # (row, label, formula, explanation)
    (
        START + 1,
        "Tax rate in [0, 1] (not a raw percentage)",
        '=IF(OR(\'1. Deal Inputs\'!$B$42>1,\'1. Deal Inputs\'!$B$42<0),'
        '"❌ FAIL — tax rate outside [0,1]; entered 26.6 instead of 0.266?",'
        '"✅ PASS")',
        "26.6 instead of 0.266 silently produces −€7/share EPS.",
    ),
    (
        START + 2,
        "Purchase price numeric and > 0",
        '=IF(OR(NOT(ISNUMBER(\'1. Deal Inputs\'!$B$15)),\'1. Deal Inputs\'!$B$15<=0),'
        '"❌ FAIL — purchase price blank or ≤ 0",'
        '"✅ PASS")',
        "PP=0 or blank → model runs on nothing, all KPIs are ÷0 or zero.",
    ),
    (
        START + 3,
        "Shares outstanding numeric and > 0",
        '=IF(OR(NOT(ISNUMBER(\'1. Deal Inputs\'!$B$44)),\'1. Deal Inputs\'!$B$44<=0),'
        '"❌ FAIL — shares outstanding blank or ≤ 0",'
        '"✅ PASS")',
        "Negative shares silently flip the EPS sign; blank makes EPS n/a.",
    ),
    (
        START + 4,
        "Closing date ≥ signing date",
        '=IF(AND(ISNUMBER(\'1. Deal Inputs\'!$B$20),ISNUMBER(\'1. Deal Inputs\'!$B$19),'
        '\'1. Deal Inputs\'!$B$20<\'1. Deal Inputs\'!$B$19),'
        '"❌ FAIL — closing date before signing date",'
        '"✅ PASS")',
        "Close before signing → nonsense dates with negative month factor.",
    ),
    (
        START + 5,
        "Horizon length in [1, 8]",
        '=IF(OR(NOT(ISNUMBER(\'1. Deal Inputs\'!$B$40)),'
        '\'1. Deal Inputs\'!$B$40<1,\'1. Deal Inputs\'!$B$40>8),'
        '"❌ FAIL — horizon outside [1,8]",'
        '"✅ PASS")',
        "Horizon > 8 silently ignored (grid is 8 cols); < 1 makes no sense.",
    ),
    (
        START + 6,
        "Financing-currency mix has at least one currency > 0%",
        '=IF(OR(NOT(ISNUMBER(\'3. Scenario & Mix\'!$C$30)),'
        '\'3. Scenario & Mix\'!$C$30<=0),'
        '"❌ FAIL — financing mix is empty (all 0%)",'
        '"✅ PASS")',
        "Empty mix → model runs with no financing currencies allocated.",
    ),
    (
        START + 7,
        "Every sale currency is in the currency list (A8:A29)",
        '=IF(SUMPRODUCT((\'3. Scenario & Mix\'!$A$86:$A$91<>"")'
        '*(COUNTIF(\'3. Scenario & Mix\'!$A$8:$A$29,\'3. Scenario & Mix\'!$A$86:$A$91)=0))>0,'
        '"❌ FAIL — a sale currency not in the currency list",'
        '"✅ PASS")',
        "Selling a currency not in the model → silent no-op.",
    ),
    (
        START + 8,
        "Every sale currency is UPPER-CASE",
        '=IF(SUMPRODUCT((\'3. Scenario & Mix\'!$A$86:$A$91<>"")'
        '*(NOT(EXACT(\'3. Scenario & Mix\'!$A$86:$A$91,'
        'UPPER(\'3. Scenario & Mix\'!$A$86:$A$91)))))>0,'
        '"❌ FAIL — a sale currency is not uppercase",'
        '"✅ PASS")',
        "Lowercase ISO codes risk case-sensitive mismatches in lookups.",
    ),
    (
        START + 9,
        "Every sale event year ≥ 1",
        '=IF(SUMPRODUCT((ISNUMBER(\'3. Scenario & Mix\'!$C$86:$C$91))'
        '*(\'3. Scenario & Mix\'!$C$86:$C$91<1))>0,'
        '"❌ FAIL — a sale event year < 1",'
        '"✅ PASS")',
        "Year 0 is accepted but the sale never fires (gating is j ≥ yr-1).",
    ),
    (
        START + 10,
        "Every sale event year ≤ horizon",
        '=IF(SUMPRODUCT((ISNUMBER(\'3. Scenario & Mix\'!$C$86:$C$91))'
        '*(\'3. Scenario & Mix\'!$C$86:$C$91>\'1. Deal Inputs\'!$B$40))>0,'
        '"❌ FAIL — a sale year exceeds the horizon",'
        '"✅ PASS")',
        "Year 9 with horizon 8 → sale never fires, silently ignored.",
    ),
]

# ── copy styling from an existing check row ─────────────────────────
ref_row = 72  # a typical check row
ref_a = ws.cell(ref_row, 1)
ref_b = ws.cell(ref_row, 2)
ref_c = ws.cell(ref_row, 3)

def copy_style(src, dst):
    if src.font:
        dst.font = copy(src.font)
    if src.alignment:
        dst.alignment = copy(src.alignment)
    if src.border:
        dst.border = copy(src.border)

# write section header
hdr = ws.cell(START, 1)
hdr_ref = ws.cell(8, 1)  # use a section-header row's style
copy_style(hdr_ref, hdr)

# write checks
for row, label, formula, explanation in checks:
    a = ws.cell(row, 1, label)
    b = ws.cell(row, 2, formula)
    c = ws.cell(row, 3, explanation)
    copy_style(ref_a, a)
    copy_style(ref_b, b)
    copy_style(ref_c, c)

# ── verify verdict range covers new checks ──────────────────────────
verdict_formula = ws.cell(5, 2).value
assert "$B$120" in verdict_formula, f"Verdict range doesn't reach row 120: {verdict_formula}"
last_check_row = START + 10  # row 99
assert last_check_row <= 120, f"Last check at row {last_check_row} > 120, verdict won't count it"

print(f"✅ Added {len(checks)} input-boundary checks at rows {START+1}–{last_check_row}")
print(f"   Section header at row {START}")
print(f"   All within verdict range B8:B120")

wb.save(DST)
print(f"   Saved → {DST}")
