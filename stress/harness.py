#!/usr/bin/env python3 -I
"""
Stress-test harness for the Henkel M&A Financing Model.
Copies the model, applies input overrides with openpyxl,
recalculates with LibreOffice headless, reads results with data_only.
Logs every run to runs.csv.
"""
import os, sys, shutil, subprocess, csv, json, time, traceback
from pathlib import Path
from datetime import datetime

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    import openpyxl
    from openpyxl.utils import get_column_letter

ORIG = "/root/.claude/uploads/f541fb74-1bf9-506f-b506-26666dd98af2/05f21222-Henkel_MA_Financing_Model_teilverkauf_meherere_verk_ufe.xlsx"
STRESS_DIR = Path("/home/user/Website/stress")
RUNS_CSV = STRESS_DIR / "runs.csv"
COUNTER = {"n": 0}

# Output cells to harvest (sheet, cell_ref, label)
OUTPUT_CELLS = [
    ("Dashboard", "B5", "model_ready"),
    ("Dashboard", "B6", "missing_inputs"),
    ("Dashboard", "B14", "dash_allin_y1"),
    ("Dashboard", "C14", "dash_amount_raised"),
    ("Dashboard", "D14", "dash_outstanding_y1"),
    ("Dashboard", "E14", "dash_interest_y1"),
    ("Dashboard", "F14", "dash_cumul_interest"),
    ("Dashboard", "G14", "dash_leverage"),
    ("Dashboard", "H14", "dash_eps_y1"),
    ("E3 · Cost & Schedule", "B8", "e3_amount_raised"),
    ("E3 · Cost & Schedule", "C54", "e3_allin_y1"),
    ("E3 · Cost & Schedule", "D54", "e3_allin_y2"),
    ("E3 · Cost & Schedule", "E54", "e3_allin_y3"),
    ("E3 · Cost & Schedule", "C60", "e3_open_bal_y1"),
    ("E3 · Cost & Schedule", "C63", "e3_close_bal_y1"),
    ("E3 · Cost & Schedule", "D63", "e3_close_bal_y2"),
    ("E3 · Cost & Schedule", "C64", "e3_avg_bal_y1"),
    ("E3 · Cost & Schedule", "C65", "e3_interest_y1"),
    ("E3 · Cost & Schedule", "D65", "e3_interest_y2"),
    ("E3 · Cost & Schedule", "E65", "e3_interest_y3"),
    ("E3 · Cost & Schedule", "C66", "e3_upfront_fees"),
    ("E3 · Cost & Schedule", "C70", "e3_net_finres_y1"),
    ("E3 · Cost & Schedule", "D70", "e3_net_finres_y2"),
    ("E4 · KPIs & Funding", "B16", "e4_leverage"),
    ("E4 · KPIs & Funding", "C54", "e4_ebit_y1"),
    ("E4 · KPIs & Funding", "C55", "e4_net_finres_y1"),
    ("E4 · KPIs & Funding", "C56", "e4_net_income_y1"),
    ("E4 · KPIs & Funding", "C57", "e4_eps_y1"),
    ("E4 · KPIs & Funding", "D57", "e4_eps_y2"),
    ("Henkel Summary", "C16", "hs_avg_eur_y1"),
    ("Henkel Summary", "C17", "hs_rate_eur_y1"),
    ("Henkel Summary", "C25", "hs_interest_eur_y1"),
    ("Henkel Summary", "C30", "hs_net_finres_y1"),
    ("Henkel Summary", "C75", "hs_interest_shed"),
    ("Henkel Summary", "C76", "hs_post_sale_interest"),
    ("Henkel Summary", "C63", "hs_retained_pct_block4"),
    ("Henkel Summary", "C78", "hs_retained_factor_block5"),
    ("Henkel Summary", "C79", "hs_op_retained"),
    ("Henkel Summary", "C80", "hs_post_sale_nfp"),
    ("Henkel Summary", "C92", "hs_post_sale_ebit"),
    ("Henkel Summary", "C93", "hs_post_sale_eps"),
    ("✓ Acceptance Test", "B5", "at_failing"),
    ("✓ Acceptance Test", "B6", "at_verdict"),
]

# Also read all individual AT checks
AT_CHECK_ROWS = list(range(9, 76))


def _parse_cell_ref(ref):
    """Parse 'C54' into (row, col)."""
    col_str = ""
    row_str = ""
    for ch in ref:
        if ch.isalpha():
            col_str += ch
        else:
            row_str += ch
    col = 0
    for ch in col_str.upper():
        col = col * 26 + (ord(ch) - ord('A') + 1)
    return int(row_str), col


def run(case_name, overrides, extra_outputs=None):
    """
    Run a stress test case.

    overrides: dict of "SheetName!CellRef" -> value
               e.g. {"1. Deal Inputs!B9": 2000}
    extra_outputs: optional list of (sheet, cell, label) to read additionally

    Returns dict of all output values.
    """
    COUNTER["n"] += 1
    run_id = f"{COUNTER['n']:04d}_{case_name}"
    copy_path = STRESS_DIR / f"{run_id}.xlsx"

    # 1. Copy original
    shutil.copy2(ORIG, copy_path)

    # 2. Apply overrides with openpyxl
    wb = openpyxl.load_workbook(copy_path)
    for cell_addr, value in overrides.items():
        sheet_name, cell_ref = cell_addr.rsplit("!", 1)
        # Strip quotes from sheet name if present
        sheet_name = sheet_name.strip("'")
        try:
            ws = wb[sheet_name]
        except KeyError:
            print(f"  WARNING: sheet '{sheet_name}' not found")
            continue
        row, col = _parse_cell_ref(cell_ref)
        cell = ws.cell(row=row, column=col)
        from openpyxl.cell.cell import MergedCell
        if isinstance(cell, MergedCell):
            # Unmerge the range containing this cell, then write
            for mr in list(ws.merged_cells.ranges):
                if cell.coordinate in mr:
                    ws.unmerge_cells(str(mr))
                    break
            cell = ws.cell(row=row, column=col)
        cell.value = value
    wb.save(copy_path)
    wb.close()

    # 3. Recalculate with LibreOffice headless
    recalc_path = _recalc_libre(copy_path)
    if recalc_path is None:
        print(f"  ERROR: LibreOffice recalc failed for {run_id}")
        return {"_error": "recalc_failed", "_case": case_name}

    # 4. Read results with data_only
    results = _read_outputs(recalc_path, extra_outputs)
    results["_case"] = case_name
    results["_run_id"] = run_id

    # 5. Read AT check details
    at_details = _read_at_checks(recalc_path)
    results["_at_checks"] = at_details
    results["_at_failing_list"] = [
        f"Row{r}: {v}" for r, v in at_details.items()
        if v and isinstance(v, str) and "❌" in v
    ]

    # 6. Log to CSV
    _log_run(results)

    # 7. Clean up the copy (keep recalculated)
    if copy_path.exists() and recalc_path != copy_path:
        copy_path.unlink()

    return results


def _recalc_libre(xlsx_path):
    """Recalculate via xlsx→ods→xlsx roundtrip (forces LO full recalc)."""
    out_dir = xlsx_path.parent
    ods_path = xlsx_path.with_suffix(".ods")
    lo_env = {**os.environ, "HOME": "/tmp/lo_home"}
    try:
        # Step 1: xlsx → ods (recalculates internally)
        r1 = subprocess.run(
            ["libreoffice", "--headless", "--calc",
             "--convert-to", "ods", "--outdir", str(out_dir), str(xlsx_path)],
            capture_output=True, text=True, timeout=120, env=lo_env
        )
        if r1.returncode != 0 or not ods_path.exists():
            print(f"  LO step1 failed: {r1.stderr[:300]}")
            return None
        # Step 2: ods → xlsx (caches recalculated values)
        r2 = subprocess.run(
            ["libreoffice", "--headless", "--calc",
             "--convert-to", "xlsx", "--outdir", str(out_dir), str(ods_path)],
            capture_output=True, text=True, timeout=120, env=lo_env
        )
        if ods_path.exists():
            ods_path.unlink()
        if r2.returncode != 0:
            print(f"  LO step2 failed: {r2.stderr[:300]}")
            return None
        return xlsx_path
    except Exception as e:
        print(f"  LO exception: {e}")
        if ods_path.exists():
            ods_path.unlink()
        return None


def _read_outputs(xlsx_path, extra_outputs=None):
    """Read all output cells from recalculated workbook."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    results = {}

    all_outputs = OUTPUT_CELLS[:]
    if extra_outputs:
        all_outputs.extend(extra_outputs)

    for sheet_name, cell_ref, label in all_outputs:
        try:
            ws = wb[sheet_name]
            row, col = _parse_cell_ref(cell_ref)
            val = ws.cell(row=row, column=col).value
            results[label] = val
        except Exception as e:
            results[label] = f"ERROR:{e}"

    wb.close()
    return results


def _read_at_checks(xlsx_path):
    """Read all Acceptance Test check rows."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["✓ Acceptance Test"]
    checks = {}
    for r in AT_CHECK_ROWS:
        val = ws.cell(row=r, column=2).value
        if val is not None:
            checks[r] = val
    wb.close()
    return checks


def _log_run(results):
    """Append run results to CSV."""
    # Filter out internal keys for CSV
    csv_data = {k: v for k, v in results.items()
                if not k.startswith("_at_checks")}

    file_exists = RUNS_CSV.exists()
    with open(RUNS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(csv_data.keys()),
                                extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow(csv_data)


def run_baseline():
    """Run the model with no changes to establish baseline values."""
    return run("BASELINE", {})


def compare(baseline, test, keys=None, tol=0.001):
    """
    Compare baseline and test results.
    Returns list of (key, baseline_val, test_val, pct_diff) for diffs > tol.
    """
    if keys is None:
        keys = [k for k in baseline if not k.startswith("_")]

    diffs = []
    for k in keys:
        bv = baseline.get(k)
        tv = test.get(k)
        if bv == tv:
            continue
        if isinstance(bv, (int, float)) and isinstance(tv, (int, float)):
            if bv != 0:
                pct = abs(tv - bv) / abs(bv)
            else:
                pct = float('inf') if tv != 0 else 0
            if pct > tol:
                diffs.append((k, bv, tv, pct))
        else:
            diffs.append((k, bv, tv, None))
    return diffs


def fmt_val(v):
    """Format a value for display."""
    if isinstance(v, float):
        if abs(v) < 0.01:
            return f"{v:.6f}"
        return f"{v:.4f}"
    return str(v)


if __name__ == "__main__":
    os.makedirs(STRESS_DIR, exist_ok=True)
    print("Running baseline...")
    bl = run_baseline()
    print(f"\nBaseline results:")
    for k in sorted(bl.keys()):
        if not k.startswith("_"):
            print(f"  {k}: {fmt_val(bl[k])}")
    print(f"\n  AT failing: {bl.get('at_failing')}")
    print(f"  AT verdict: {bl.get('at_verdict')}")
    if bl.get("_at_failing_list"):
        for f in bl["_at_failing_list"]:
            print(f"    {f}")
