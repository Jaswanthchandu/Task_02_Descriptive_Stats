import sys
import pandas as pd

MISSING_TOKENS = ["", "NA", "N/A", "null", "NULL", "None", "NaN", "-"]
TOP_N = 15
GROUP_METRICS = ["estimated_spend", "estimated_impressions"]


def clean_numeric(series):
    stripped = (series.astype(str)
                      .str.replace(r"[$,%]", "", regex=True)
                      .str.strip())
    return pd.to_numeric(stripped, errors="coerce")


def main():
    if len(sys.argv) != 2:
        print("Usage: python pandas_stats.py path/to/dataset.csv")
        sys.exit(1)
    path = sys.argv[1]

    df = pd.read_csv(path, na_values=MISSING_TOKENS, keep_default_na=True,
                     low_memory=False)

    print("=" * 72)
    print(f"DATASET: {path}")
    print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print("=" * 72)

    
    numeric_cols, categorical_cols = [], []
    for col in df.columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            categorical_cols.append(col)
            continue
        if clean_numeric(non_null).notna().mean() >= 0.8:
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    print("\nCOLUMN OVERVIEW (missing | type)")
    print("-" * 72)
    for col in df.columns:
        miss = int(df[col].isna().sum())
        pct = miss / len(df) * 100
        ctype = "numeric" if col in numeric_cols else "categorical"
        print(f"{col:<42} {miss:>8,} ({pct:5.1f}%)  {ctype}")

    print("\nNUMERIC COLUMNS (dataset level)")
    print("-" * 72)
    for col in numeric_cols:
        nums = clean_numeric(df[col]).dropna()
        print(f"\n{col}")
        print(f"  count={nums.count():,}  mean={nums.mean():,.4f}  "
              f"median={nums.median():,.4f}")
        print(f"  min={nums.min():,.4f}  max={nums.max():,.4f}  "
              f"std={nums.std():,.4f}")   # ddof=1 by default

    print("\nCATEGORICAL COLUMNS (dataset level)")
    print("-" * 72)
    for col in categorical_cols:
        s = df[col].dropna().astype(str)
        vc = s.value_counts()
        if len(vc) == 0:
            continue
        print(f"\n{col}")
        print(f"  count={s.count():,}  unique={s.nunique():,}  "
              f"mode='{vc.index[0]}' (x{int(vc.iloc[0]):,})")
        for value, freq in vc.head(5).items():
            disp = value if len(value) <= 60 else value[:57] + "..."
            print(f"    {int(freq):>8,}  {disp}")

    # --- Grouped by page_id ---
    for m in GROUP_METRICS:
        df[m + "_num"] = clean_numeric(df[m])

    print("\n" + "=" * 72)
    print("GROUPED BY page_id")
    print("=" * 72)
    grp = df.groupby("page_id").agg(
        ads=("ad_id", "size"),
        total_spend=("estimated_spend_num", "sum"),
        mean_spend=("estimated_spend_num", "mean"),
        total_impr=("estimated_impressions_num", "sum"),
    )
    print(f"Unique page_id groups: {grp.shape[0]:,}")
    top = grp.sort_values("ads", ascending=False).head(TOP_N)
    print(f"\nTop {TOP_N} pages by ad count:")
    print(f"{'page_id (first 20 chars)':<24} {'ads':>8} {'total_spend':>14} "
          f"{'mean_spend':>12} {'total_impr':>14}")
    for pid, r in top.iterrows():
        print(f"{pid[:20]:<24} {int(r['ads']):>8,} {r['total_spend']:>14,.0f} "
              f"{r['mean_spend']:>12,.1f} {r['total_impr']:>14,.0f}")

    # --- Grouped by (page_id, ad_id) ---
    n_pairs = df.groupby(["page_id", "ad_id"]).ngroups
    print("\n" + "=" * 72)
    print("GROUPED BY (page_id, ad_id)")
    print("=" * 72)
    print(f"Unique (page_id, ad_id) groups: {n_pairs:,}")
    print(f"Total rows: {len(df):,}")
    if n_pairs == len(df):
        print("Each (page_id, ad_id) pair is unique - one row per ad.")
    else:
        print(f"{len(df) - n_pairs:,} rows share a (page_id, ad_id) pair.")


if __name__ == "__main__":
    main()
