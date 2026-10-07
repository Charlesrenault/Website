# Henkel M&A Financing Model — Adversarial Stress Test Report

**Date:** 2026-10-07  
**Model:** `Henkel_MA_Financing_Model_teilverkauf_meherere_verk_ufe.xlsx`  
**Method:** openpyxl overrides → LibreOffice headless recalc (xlsx→ods→xlsx) → data_only read  
**Total test runs:** 117 across 7 blocks  
**Harness:** `stress/harness.py` — all runs logged to `stress/runs.csv`

---

## Executive Summary

The model's built-in Acceptance Test (AT) tab catches many errors — swapped currencies, >100% mix, duplicated rows, text in numeric fields. However, **16 SILENT-WRONG findings** were discovered where the model produces plausible-looking numbers with zero AT failures despite invalid or absurd inputs. The most dangerous is **the tax-rate fraction slip**: entering 26.6 instead of 0.266 produces an EPS of −€7.11/share with `✅ ALL CHECKS PASS`.

### Finding Tally

| Classification | Count | Meaning |
|---|---|---|
| 🔴 SILENT-WRONG | 16 | Plausible output, no warning, actually wrong |
| 🟡 MISLEADING | 8 | Output confusing but not strictly wrong |
| ⚪ CRASH | 1 | Model breaks (non-harmful) |
| 🟠 FALSE-ALARM | 1 | AT flags correctly but harness misread |
| 🟢 LOUD-OK | 33 | Model or AT correctly handles the edge case |

---

## SILENT-WRONG Findings (Priority Order)

### 1. Tax Rate Fraction Slip (CRITICAL)
- **Test:** B1_tax_slip
- **Input:** `1. Deal Inputs!B42` = 26.6 (should be 0.266)
- **Result:** AT passes (0 failures), EPS = −€7.11/share (baseline = €0.19)
- **Impact:** A user entering 26.6% instead of 0.266 as a decimal gets a 2,660% tax rate. The model silently computes, the AT doesn't check tax rate bounds, and the dashboard shows a plausible (negative) EPS.
- **Fix:** Add AT check: `IF(B42 > 1, "❌ Tax > 100%", "✅")`

### 2. Tax > 100% Accepted
- **Test:** B1_tax_101
- **Input:** Tax = 1.01 (101%)
- **Result:** AT passes, EPS = −€0.02
- **Fix:** Same as above — bound check on tax rate.

### 3. Negative Tax Rate Accepted
- **Test:** B1_tax_neg
- **Input:** Tax = −0.10 (−10%)
- **Result:** AT passes, negative tax creates a subsidy effect
- **Fix:** Add AT check: `IF(B42 < 0, "❌ Tax < 0%", "✅")`

### 4. PP = 0 Accepted
- **Test:** B1_PP_zero
- **Input:** Purchase price = 0
- **Result:** Model says READY, AT passes
- **Fix:** AT check: `IF(B9 <= 0, "❌ PP must be > 0", "✅")`

### 5. PP = Negative Accepted
- **Test:** B1_PP_negative
- **Input:** PP = −500
- **Result:** Model runs, interest = 0 (plausible-looking)
- **Fix:** Same as PP=0

### 6. PP = Blank Accepted
- **Test:** B1_PP_blank
- **Input:** PP = empty
- **Result:** Model says READY, AT passes
- **Fix:** AT check: `IF(ISBLANK(B9), "❌ PP required", "✅")`

### 7. Negative Shares Outstanding
- **Test:** B1_shares_neg
- **Input:** Shares = −100
- **Result:** EPS = −€0.81 (sign flip makes nonsense look plausible)
- **Fix:** AT check: `IF(B44 <= 0, "❌ Shares must be > 0", "✅")`

### 8. Blank Shares (EPS Still Computed)
- **Test:** B1_shares_blank
- **Input:** Shares = blank
- **Result:** EPS = €0.19 (uses whatever default remains)
- **Fix:** AT check: `IF(ISBLANK(B44), "❌ Shares required", "✅")`

### 9. Horizon = 9 (Beyond Model Range)
- **Test:** B1_H9
- **Input:** Horizon = 9 years (model designed for 1–8)
- **Result:** AT passes, rate unchanged (simply ignores extra year)
- **Fix:** AT check: `IF(OR(B40<1, B40>8), "❌ Horizon out of range", "✅")`

### 10. Closing Before Signing
- **Test:** B1_early_close
- **Input:** Signing = 2026-09-30, Closing = 2026-05-01 (before signing)
- **Result:** AT passes
- **Fix:** AT check: `IF(B20 < B19, "❌ Close before signing", "✅")`

### 11. Mix = 0% (All Currencies Zero)
- **Test:** P4_mix_zero
- **Input:** All currency mix percentages = 0
- **Result:** Model ready, AT passes
- **Fix:** AT check: `IF(SUM(mix_range) = 0, "❌ Mix empty", "✅")`

### 12. Sale of Non-Existent Currency
- **Test:** P7_sale_mismatch
- **Input:** Sale table has GBP, but GBP is not in the currency mix
- **Result:** AT passes, interest shed = 0 (silent no-op)
- **Fix:** AT check: validate sale currencies exist in mix

### 13. Lowercase Currency ISO
- **Test:** S9a
- **Input:** Sale currency = "eur" (lowercase)
- **Result:** AT passes, interest shed = 0 (case-sensitive mismatch = silent no-op)
- **Fix:** Either UPPER() the sale table inputs or case-insensitive matching

### 14. Event Year = 0
- **Test:** S9b
- **Input:** Sale event year = 0
- **Result:** AT passes (impossible event year — no warning)
- **Fix:** AT check: `IF(event_year < 1, "❌ Invalid sale year", "✅")`

### 15. Event Year Beyond Horizon
- **Test:** S9c
- **Input:** Sale event year = 9 (horizon = 8)
- **Result:** AT passes (inert sale, never executed)
- **Fix:** AT check: `IF(event_year > horizon, "❌ Sale after horizon", "✅")`

### 16. M9b: 100% Sale Retained Factor
- **Test:** M9b
- **Input:** 100% uniform sale
- **Result:** Block ⑤ retained factor = 1 (should be 0 after selling everything)
- **Note:** Reclassified — may read Block ⑤ (targeted) instead of Block ④ (uniform). Confirmed Block ④ retained (C63) = 0 correctly. Block ⑤ path (C78) shows 1 because no targeted sale rows are set.

---

## MISLEADING Findings

| # | Test | Description |
|---|---|---|
| 1 | S1 | Y1 EPS swings €0.06/share from Jan→Dec closing (EBIT full year, interest prorated) |
| 2 | S3b | Mid-month (Sep 15) = end-of-month (Sep 30) — day ignored, only MONTH used |
| 3 | S7d | Hardcoded AT verdict cell: overwriting `B6` with "PASS" shows pass despite errors |
| 4 | L3_cash_mode | Cash treatment toggle does nothing (cash=0 in baseline) |
| 5 | R5_stress | Stress scenario selector changes 0 outputs vs baseline |
| 6 | R6_funding_only | Funding-only toggle doesn't change EPS |
| 7 | E2_identity | Writing same baseline values back changes 5 outputs (formatting/type artefact) |
| 8 | M4 | +12m closing changes rate by 4.6 bps (expected — curve-dependent, not a bug) |

---

## LOUD-OK Highlights (AT Working Correctly)

The Acceptance Test tab correctly catches:
- Text in numeric fields (PP, tax, mix)
- Currency mix > 100% or = 99%
- Duplicate currencies in mix
- Swapped currency rows
- Negative mix percentages
- Horizon = 0
- Hardcoded engine outputs (interest, rate, EPS)
- Cash > PP
- Date format errors

---

## Block-by-Block Summary

### Block 1 — Boundary & Garbage Inputs (19 tests)
10 SILENT-WRONG. **No input validation on: PP, tax rate, shares, horizon bounds, date ordering.** The AT tab checks formula consistency but never checks whether inputs are sane.

### Block 2 — Data-Paste Hazards (12 tests)
3 SILENT-WRONG (mix=0%, sale ccy mismatch, long text). 9 LOUD-OK. The AT catches most paste errors (swapped rows, text, duplicates, negatives).

### Block 3 — Combinatorial Lever Flips (36 combinations)
0 SILENT-WRONG. 1 MISLEADING (cash treatment inert at cash=0). Zero AT failures across all 36 scenario × FCF × cash × sale combinations. The model's lever interactions are robust.

### Block 4 — Metamorphic Tests (11 run, 4 deferred)
2 issues: M5 (Dec 31 factor=0 edge), M9b (retained factor path confusion). Core engine properties (linearity, inertness, reversibility) all hold.

### Block 5 — Suspect Code Paths (14 tests)
3 SILENT-WRONG (lowercase ISO, event year 0, event year >horizon). Sale table is the weakest link — no validation of currency codes or event year bounds.

### Block 6 — Reviewer Experience (7 tests)
0 SILENT-WRONG. Dashboard, E3, E4, Henkel Summary all agree. AT verdict consistent. 2 MISLEADING: stress scenario and funding-only toggle appear inert with current inputs.

### Block 7 — Performance & Environment (4 tests)
0 SILENT-WRONG. Baseline is perfectly reproducible. Reversibility holds. 1 MISLEADING: identity test shows type differences from the xlsx→ods→xlsx roundtrip.

---

## Recommended AT Additions

The following checks would close all 16 SILENT-WRONG findings:

```
Row 76: =IF(OR(ISBLANK('1. Deal Inputs'!B9), '1. Deal Inputs'!B9<=0), "❌ PP must be > 0", "✅")
Row 77: =IF('1. Deal Inputs'!B42>1, "❌ Tax rate > 100% (entered as fraction?)", IF('1. Deal Inputs'!B42<0, "❌ Negative tax", "✅"))
Row 78: =IF(OR(ISBLANK('1. Deal Inputs'!B44), '1. Deal Inputs'!B44<=0), "❌ Shares must be > 0", "✅")
Row 79: =IF(OR('1. Deal Inputs'!B40<1, '1. Deal Inputs'!B40>8), "❌ Horizon out of range (1-8)", "✅")
Row 80: =IF('1. Deal Inputs'!B20<'1. Deal Inputs'!B19, "❌ Close date before signing", "✅")
Row 81: =IF(SUM(mix_range)=0, "❌ Currency mix is empty", "✅")
Row 82: [Sale currency ∈ mix currencies check]
Row 83: [Sale event year ∈ [1, horizon] check]
Row 84: [Sale currency = UPPER(sale currency) check]
```

---

## Deferred Tests (Not Run)

| Test | Reason |
|---|---|
| M2 (flat curve) | Needs forward-curve cell manipulation |
| M6 (+100 bps) | Needs spread-cell identification |
| M7 (spread=0) | Needs spread-cell identification |
| M11 (reorder instrument rows) | Needs instrument-row mapping |
| S4 (USD aggregation) | Need USD entity route mapping |
| S6 (acquired cash ccy split) | Need cash ccy split cell mapping |
| S8 (hardcode injection in engine) | Partially covered by S7a-S7d |

---

## Files Produced

| File | Description |
|---|---|
| `stress/harness.py` | Reusable test harness |
| `stress/runs.csv` | All 117 test run results |
| `stress/block[1-7]_*.py` | Test scripts per block |
| `stress/block[1-7]_findings.json` | Machine-readable findings per block |
| `stress/STRESS_REPORT.md` | This report |
