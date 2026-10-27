"""Split entity structuring into external vs internal views.

Distinction:
  EXTERNAL (real group cost):  FX hedge + bank/facility fee
  INTERNAL (consolidation wash): IC margin + cash-pool spread

Changes:
  Tab 3:  cols I,J added per entity row (64-71) + summary (72)
          H renamed "Total entity spread"; I = external; J = internal
          H formula updated to recognise "Equity" route (zero cost)
          Note row 73 updated

  E4:     row 35: sub-headers; row 36 cols C,D: external/internal weighted
          (B36 = total stays unchanged)

  E3:     B51 label clarified (total incl. internal)
          B52 = external-only entity cost (reads E4 C36)
          Row 55 = GROUP ALL-IN RATE (external entity costs only)
"""

import openpyxl
from copy import copy

SRC = "/mnt/user-data/outputs/Henkel_MA_Financing_Model_teilverkauf_ccy.xlsx"
DST = SRC

wb = openpyxl.load_workbook(SRC)
ws_mix = wb["3. Scenario & Mix"]
ws_e4  = wb["E4 · KPIs & Funding"]
ws_e3  = wb["E3 · Cost & Schedule"]


def copy_style(src, dst):
    for attr in ("font", "alignment", "border", "fill", "number_format"):
        v = getattr(src, attr, None)
        if v:
            setattr(dst, attr, copy(v))


# ── 1. TAB 3: column headers at row 63 ──────────────────────────────

ws_mix.cell(63, 8, "Total entity spread (bps)")
ws_mix.cell(63, 9, "of which: external (bps)")
ws_mix.cell(63, 10, "of which: internal (bps)")

# Style new headers from existing col-H header
for c in (9, 10):
    copy_style(ws_mix.cell(63, 8), ws_mix.cell(63, c))


# ── 2. TAB 3: update H formula + add I,J for rows 64-71 ─────────────

E4 = "'E4 · KPIs & Funding'"

for row in range(64, 72):
    # H — total entity spread (now with Equity route = 0)
    h = (
        f'=IF($A{row}="","",IF(ISNUMBER($G{row}),$G{row},'
        f'IF($E{row}="IC Loan",{E4}!$B$24+{E4}!$B$25,'
        f'IF($E{row}="Equity",0,{E4}!$B$27))'
        f'+IF($F{row}="Y",{E4}!$B$26,0)))'
    )
    ws_mix.cell(row, 8, h)

    # I — external costs (real cash out the door: bank fee + hedge)
    i = (
        f'=IF($A{row}="","",'
        f'IF($E{row}="Local External",{E4}!$B$27,0)'
        f'+IF($F{row}="Y",{E4}!$B$26,0))'
    )
    ws_mix.cell(row, 9, i)
    copy_style(ws_mix.cell(row, 8), ws_mix.cell(row, 9))

    # J — internal allocation (IC margin + pool, washes at consolidation)
    j = (
        f'=IF($A{row}="","",'
        f'IF($E{row}="IC Loan",{E4}!$B$24+{E4}!$B$25,0))'
    )
    ws_mix.cell(row, 10, j)
    copy_style(ws_mix.cell(row, 8), ws_mix.cell(row, 10))


# ── 3. TAB 3: summary row 72 — add I,J weighted averages ────────────

# I72: weighted external
ws_mix.cell(72, 9,
    "=IFERROR(SUMPRODUCT($D$64:$D$71,$I$64:$I$71)"
    "/SUM($D$64:$D$71),0)")
copy_style(ws_mix.cell(72, 8), ws_mix.cell(72, 9))

# J72: weighted internal
ws_mix.cell(72, 10,
    "=IFERROR(SUMPRODUCT($D$64:$D$71,$J$64:$J$71)"
    "/SUM($D$64:$D$71),0)")
copy_style(ws_mix.cell(72, 8), ws_mix.cell(72, 10))


# ── 4. TAB 3: update note row 73 ────────────────────────────────────

ws_mix.cell(73, 1,
    "► Routes: IC Loan (margin+pool = internal), Local External (bank fee = external), "
    "Equity (zero cost — parent capitalises sub).  "
    "Hedging is always external.  "
    "G overrides total (H); I/J show standard split regardless.  "
    "Blank rows ignored.")


# ── 5. E4: split view on rows 35-36 ─────────────────────────────────

# Unmerge D36:J36 that would block writes
to_unmerge = []
for mr in ws_e4.merged_cells.ranges:
    if mr.min_row == 36 and mr.max_row == 36 and mr.min_col >= 4:
        to_unmerge.append(str(mr))
for mr_str in to_unmerge:
    ws_e4.unmerge_cells(mr_str)
    print(f"  unmerged E4 {mr_str}")

# Row 35: sub-headers
ws_e4.cell(35, 2, "Total")
ws_e4.cell(35, 3, "External (real)")
ws_e4.cell(35, 4, "Internal (wash)")

# Row 36: values
# B36 stays unchanged (total) — already correct
# C36: external weighted
ws_e4.cell(36, 3,
    "=IFERROR(SUMPRODUCT('3. Scenario & Mix'!$D$64:$D$71,"
    "'3. Scenario & Mix'!$I$64:$I$71)"
    "/SUM('3. Scenario & Mix'!$D$64:$D$71),0)")

# D36: internal weighted
ws_e4.cell(36, 4,
    "=IFERROR(SUMPRODUCT('3. Scenario & Mix'!$D$64:$D$71,"
    "'3. Scenario & Mix'!$J$64:$J$71)"
    "/SUM('3. Scenario & Mix'!$D$64:$D$71),0)")

# Update A36 label
ws_e4.cell(36, 1,
    "► Entity structuring spread (bps, PP-share-weighted) → E3 all-in")

# E36: explanatory note (replaces old D36 note)
ws_e4.cell(36, 5,
    "External = hedge + bank fee (real cost); "
    "Internal = IC margin + pool (group wash). Total feeds E3 all-in rate.")


# ── 6. E3: clarify B51 label + add B52 external-only ────────────────

# Unmerge D51:K51 so we can write
to_unmerge = []
for mr in ws_e3.merged_cells.ranges:
    if mr.min_row == 51 and mr.max_row == 51:
        to_unmerge.append(str(mr))
for mr_str in to_unmerge:
    ws_e3.unmerge_cells(mr_str)
    print(f"  unmerged E3 {mr_str}")

ws_e3.cell(51, 1,
    "Entity structuring add (bps, TOTAL incl. internal IC alloc.) — from E4")
# B51 stays: =IFERROR('E4 · KPIs & Funding'!$B$36,0)

ws_e3.cell(52, 1,
    "  ↳ of which: group-external only (hedge + bank fee)")
ws_e3.cell(52, 2,
    "=IFERROR('E4 · KPIs & Funding'!$C$36,0)")
ws_e3.cell(52, 4,
    "← real incremental group cost; internal IC margin/pool washes at consolidation")
copy_style(ws_e3.cell(51, 1), ws_e3.cell(52, 1))
copy_style(ws_e3.cell(51, 2), ws_e3.cell(52, 2))


# ── 7. E3: row 55 — GROUP ALL-IN RATE (external entity costs only) ──

ws_e3.cell(55, 1,
    "GROUP ALL-IN RATE (external entity costs only — excl. IC margin / pool)")
ws_e3.cell(55, 2, None)
copy_style(ws_e3.cell(54, 1), ws_e3.cell(55, 1))

# Build the same formula as row 54, but with $B$52/10000 instead of $B$51/10000
# Read the C54 formula and adapt
c54_formula = ws_e3.cell(54, 3).value

for col in range(3, 11):  # C through J (8 years)
    f54 = ws_e3.cell(54, col).value
    if f54 and isinstance(f54, str) and f54.startswith("="):
        # Replace $B$51 with $B$52
        f55 = f54.replace("$B$51", "$B$52")
        ws_e3.cell(55, col, f55)
        copy_style(ws_e3.cell(54, col), ws_e3.cell(55, col))

# Also add a note at D55
ws_e3.cell(55, 11,
    "← same as row 54 but entity cost = external only (hedge + bank fee)")


# ── SAVE ──────────────────────────────────────────────────────────────

wb.save(DST)

print()
print("Done. Split view added:")
print("  Tab 3 cols I,J: per-entity external/internal split")
print("  Tab 3 H: updated with 'Equity' route (zero cost)")
print("  E4 row 35-36: weighted split (Total / External / Internal)")
print("  E3 B52: group-external entity cost")
print("  E3 row 55: GROUP ALL-IN RATE (external only)")
print(f"  Saved → {DST}")
