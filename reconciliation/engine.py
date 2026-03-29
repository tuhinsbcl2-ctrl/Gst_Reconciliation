"""
reconciliation/engine.py — Pandas-based GST reconciliation logic.

Each function accepts one or more DataFrames (loaded from Excel) and returns
a result DataFrame categorising records as:

    Matched | Missing in Source A | Missing in Source B | Amount Mismatch
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Column-name constants (callers must rename their columns to match these)
# ---------------------------------------------------------------------------

COL_GSTIN = "GSTIN"
COL_INVOICE_NO = "InvoiceNo"
COL_TAXABLE_VALUE = "TaxableValue"
COL_IGST = "IGST"
COL_CGST = "CGST"
COL_SGST = "SGST"
COL_TOTAL_TAX = "TotalTax"
COL_TAX_RATE = "TaxRate"
COL_PERIOD = "Period"  # "YYYY-MM" or "MM-YYYY"

# Result category labels
CAT_MATCHED = "Matched"
CAT_MISSING_A = "Missing in Source A"
CAT_MISSING_B = "Missing in Source B"
CAT_MISMATCH = "Amount Mismatch"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _normalise_gstin(series: pd.Series) -> pd.Series:
    """Upper-case and strip whitespace from a GSTIN column."""
    return series.astype(str).str.strip().str.upper()


def _safe_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Coerce listed columns to numeric, replacing errors with 0."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


# ---------------------------------------------------------------------------
# 1. GSTR-1 vs GSTR-3B
# ---------------------------------------------------------------------------

def reconcile_gstr1_vs_gstr3b(
    gstr1_df: pd.DataFrame,
    gstr3b_df: pd.DataFrame,
    period_col: str = COL_PERIOD,
) -> pd.DataFrame:
    """Compare sales declared in GSTR-1 with tax paid in GSTR-3B.

    Groups both DataFrames by *period_col* and computes totals for
    TaxableValue and TotalTax, then computes the variance.

    Args:
        gstr1_df:   DataFrame from GSTR-1 Excel.  Must contain columns
                    [Period, TaxableValue, TotalTax].
        gstr3b_df:  DataFrame from GSTR-3B Excel.  Same columns required.
        period_col: Column name to group by (default "Period").

    Returns:
        DataFrame with columns:
            Period | GSTR1_TaxableValue | GSTR3B_TaxableValue | TaxableValue_Diff
            | GSTR1_TotalTax | GSTR3B_TotalTax | TotalTax_Diff | Status
    """
    numeric_cols = [COL_TAXABLE_VALUE, COL_TOTAL_TAX]
    gstr1 = _safe_numeric(gstr1_df, numeric_cols)
    gstr3b = _safe_numeric(gstr3b_df, numeric_cols)

    g1_summary = (
        gstr1.groupby(period_col)[[COL_TAXABLE_VALUE, COL_TOTAL_TAX]]
        .sum()
        .rename(columns={COL_TAXABLE_VALUE: "GSTR1_TaxableValue", COL_TOTAL_TAX: "GSTR1_TotalTax"})
    )
    g3b_summary = (
        gstr3b.groupby(period_col)[[COL_TAXABLE_VALUE, COL_TOTAL_TAX]]
        .sum()
        .rename(columns={COL_TAXABLE_VALUE: "GSTR3B_TaxableValue", COL_TOTAL_TAX: "GSTR3B_TotalTax"})
    )

    merged = g1_summary.join(g3b_summary, how="outer").fillna(0).reset_index()
    merged["TaxableValue_Diff"] = merged["GSTR1_TaxableValue"] - merged["GSTR3B_TaxableValue"]
    merged["TotalTax_Diff"] = merged["GSTR1_TotalTax"] - merged["GSTR3B_TotalTax"]

    def _status(row: pd.Series) -> str:
        if row["TaxableValue_Diff"] == 0 and row["TotalTax_Diff"] == 0:
            return CAT_MATCHED
        return CAT_MISMATCH

    merged["Status"] = merged.apply(_status, axis=1)
    return merged


# ---------------------------------------------------------------------------
# 2. GSTR-2B vs GSTR-3B (ITC comparison)
# ---------------------------------------------------------------------------

def reconcile_gstr2b_vs_gstr3b(
    gstr2b_df: pd.DataFrame,
    gstr3b_df: pd.DataFrame,
    period_col: str = COL_PERIOD,
) -> pd.DataFrame:
    """Compare ITC available in GSTR-2B with ITC claimed in GSTR-3B.

    Args:
        gstr2b_df:  DataFrame from GSTR-2B Excel.  Columns: [Period, TotalTax].
        gstr3b_df:  DataFrame from GSTR-3B Excel.  Columns: [Period, TotalTax].

    Returns:
        DataFrame with columns:
            Period | GSTR2B_ITC | GSTR3B_ITC | ITC_Diff | Status
    """
    gstr2b = _safe_numeric(gstr2b_df, [COL_TOTAL_TAX])
    gstr3b = _safe_numeric(gstr3b_df, [COL_TOTAL_TAX])

    g2b = (
        gstr2b.groupby(period_col)[COL_TOTAL_TAX]
        .sum()
        .rename("GSTR2B_ITC")
    )
    g3b = (
        gstr3b.groupby(period_col)[COL_TOTAL_TAX]
        .sum()
        .rename("GSTR3B_ITC")
    )

    merged = g2b.to_frame().join(g3b, how="outer").fillna(0).reset_index()
    merged["ITC_Diff"] = merged["GSTR2B_ITC"] - merged["GSTR3B_ITC"]

    def _status(row: pd.Series) -> str:
        if row["ITC_Diff"] == 0:
            return CAT_MATCHED
        if row["ITC_Diff"] > 0:
            return "Under-claimed ITC"
        return "Over-claimed ITC"

    merged["Status"] = merged.apply(_status, axis=1)
    return merged


# ---------------------------------------------------------------------------
# 3. GSTR-2A vs GSTR-2B (missing invoice detection)
# ---------------------------------------------------------------------------

def reconcile_gstr2a_vs_gstr2b(
    gstr2a_df: pd.DataFrame,
    gstr2b_df: pd.DataFrame,
) -> pd.DataFrame:
    """Find invoices present in one return but missing in the other.

    Matches on (GSTIN + InvoiceNo).

    Args:
        gstr2a_df:  DataFrame from GSTR-2A Excel.  Columns: [GSTIN, InvoiceNo, ...].
        gstr2b_df:  DataFrame from GSTR-2B Excel.  Columns: [GSTIN, InvoiceNo, ...].

    Returns:
        Combined DataFrame with a 'Status' column indicating:
            Matched | Missing in Source A (2A) | Missing in Source B (2B)
    """
    key_cols = [COL_GSTIN, COL_INVOICE_NO]
    g2a = gstr2a_df.copy()
    g2b = gstr2b_df.copy()

    g2a[COL_GSTIN] = _normalise_gstin(g2a[COL_GSTIN])
    g2b[COL_GSTIN] = _normalise_gstin(g2b[COL_GSTIN])

    g2a["_key"] = g2a[COL_GSTIN] + "|" + g2a[COL_INVOICE_NO].astype(str).str.strip()
    g2b["_key"] = g2b[COL_GSTIN] + "|" + g2b[COL_INVOICE_NO].astype(str).str.strip()

    g2a["_source"] = "GSTR-2A"
    g2b["_source"] = "GSTR-2B"

    # Outer-join on the composite key
    merged = pd.merge(
        g2a,
        g2b,
        on="_key",
        how="outer",
        suffixes=("_2A", "_2B"),
    )

    def _status(row: pd.Series) -> str:
        has_a = pd.notna(row.get(f"{COL_GSTIN}_2A", None)) and row.get(f"{COL_GSTIN}_2A", "") != ""
        has_b = pd.notna(row.get(f"{COL_GSTIN}_2B", None)) and row.get(f"{COL_GSTIN}_2B", "") != ""
        if has_a and has_b:
            return CAT_MATCHED
        if has_a:
            return CAT_MISSING_B  # exists in 2A, missing in 2B
        return CAT_MISSING_A  # exists in 2B, missing in 2A

    merged["Status"] = merged.apply(_status, axis=1)
    merged.drop(columns=["_key", "_source_2A", "_source_2B"], errors="ignore", inplace=True)
    return merged


# ---------------------------------------------------------------------------
# 4. General invoice-level reconciliation
# ---------------------------------------------------------------------------

def reconcile_invoices(
    source_a: pd.DataFrame,
    source_b: pd.DataFrame,
    label_a: str = "Source A",
    label_b: str = "Source B",
    amount_tolerance: float = 0.01,
) -> pd.DataFrame:
    """Match invoices from two DataFrames on GSTIN + InvoiceNo.

    Args:
        source_a:          First DataFrame.  Must contain [GSTIN, InvoiceNo, TaxableValue, TotalTax].
        source_b:          Second DataFrame.  Same columns.
        label_a:           Descriptive name for source A (used in Status labels).
        label_b:           Descriptive name for source B.
        amount_tolerance:  Absolute tolerance for numeric comparisons (default 0.01).

    Returns:
        DataFrame with all rows from both sources and a 'Status' column.
    """
    numeric_cols = [COL_TAXABLE_VALUE, COL_TOTAL_TAX]
    a = _safe_numeric(source_a, numeric_cols).copy()
    b = _safe_numeric(source_b, numeric_cols).copy()

    a[COL_GSTIN] = _normalise_gstin(a[COL_GSTIN])
    b[COL_GSTIN] = _normalise_gstin(b[COL_GSTIN])

    key = [COL_GSTIN, COL_INVOICE_NO]
    merged = pd.merge(a, b, on=key, how="outer", suffixes=(f"_{label_a}", f"_{label_b}"))

    tv_a = f"{COL_TAXABLE_VALUE}_{label_a}"
    tv_b = f"{COL_TAXABLE_VALUE}_{label_b}"
    tt_a = f"{COL_TOTAL_TAX}_{label_a}"
    tt_b = f"{COL_TOTAL_TAX}_{label_b}"

    merged.fillna(
        {tv_a: 0, tv_b: 0, tt_a: 0, tt_b: 0},
        inplace=True,
    )

    def _status(row: pd.Series) -> str:
        a_present = row[tv_a] != 0 or row[tt_a] != 0
        b_present = row[tv_b] != 0 or row[tt_b] != 0
        if not a_present:
            return f"Missing in {label_a}"
        if not b_present:
            return f"Missing in {label_b}"
        tv_diff = abs(row[tv_a] - row[tv_b])
        tt_diff = abs(row[tt_a] - row[tt_b])
        if tv_diff <= amount_tolerance and tt_diff <= amount_tolerance:
            return CAT_MATCHED
        return CAT_MISMATCH

    merged["Status"] = merged.apply(_status, axis=1)
    return merged
