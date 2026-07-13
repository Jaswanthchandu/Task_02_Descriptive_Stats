
import sys
import polars as pl

MISSING_TOKENS = ["", "NA", "N/A", "null", "NULL", "None", "NaN", "-"]
TOP_N = 15
GROUP_METRICS = ["estimated_spend", "estimated_impressions"]


def clean_numeric_expr(col):
    """Expression: strip $ , % then cast to float (invalid -> null)."""
    return (pl.col(col)
              .str.replace_all(r"[$,%]", "")
              .str.strip_chars()
              .cast(pl.Float64, strict=False))


def main():
    if len(sys.argv) != 2:
        print("Usage: python polars_stats.py path/to/dataset.csv")
        sys.exit(1)
    path = sys.argv[1]

    # infer_schema_length=0 reads every column as string, so our own numeric
    # cleaning decides types - matching the other two scripts exactly.
    df = pl.read_csv(path, infer_schema_length=0, null_values=MISSING_TOKENS)

    n_rows = df.height
    print("=" * 72)
    print(f"DATASET: {path}")
    print(f"Shape: {n_rows:,} rows x {df.width} columns")
    print("=" * 72)

    # Classified each column numeric vs categorical.
    numeric_cols, categorical_cols = [], []
    for col in df.columns:
        non_null = df.select(pl.col(col).drop_nulls())
        total = non_null.height
        if total == 0:
            categorical_cols.append(col)
            continue
        parsed_ok = non_null.select(
            clean_numeric_expr(col).is_not_null().sum()
        ).item()
        if parsed_ok / total >= 0.8:
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    print("\nCOLUMN OVERVIEW (missing | type)")
    print("-" * 72)
    for col in df.columns:
        miss = df.select(pl.col(col).is_null().sum()).item()
        pct = miss / n_rows * 100 if n_rows else 0
        ctype = "numeric" if col in numeric_cols else "categorical"
        print(f"{col:<42} {miss:>8,} ({pct:5.1f}%)  {ctype}")

    print("\nNUMERIC COLUMNS (dataset level)")
    print("-" * 72)
    for col in numeric_cols:
        stats = df.select(
            clean_numeric_expr(col).count().alias("count"),
            clean_numeric_expr(col).mean().alias("mean"),
            clean_numeric_expr(col).median().alias("median"),
            clean_numeric_expr(col).min().alias("min"),
            clean_numeric_expr(col).max().alias("max"),
            clean_numeric_expr(col).std().alias("std"),   # ddof=1 default
        ).row(0, named=True)
        print(f"\n{col}")
        print(f"  count={stats['count']:,}  mean={stats['mean']:,.4f}  "
              f"median={stats['median']:,.4f}")
        print(f"  min={stats['min']:,.4f}  max={stats['max']:,.4f}  "
              f"std={stats['std']:,.4f}")

    print("\nCATEGORICAL COLUMNS (dataset level)")
    print("-" * 72)
    for col in categorical_cols:
        vc = (df.select(pl.col(col).drop_nulls())
                .get_column(col)
                .value_counts(sort=True))
        if vc.height == 0:
            continue
        count_col = "count" if "count" in vc.columns else vc.columns[-1]
        total = vc.select(pl.col(count_col).sum()).item()
        top = vc.head(5)
        mode_val = top.row(0)[0]
        mode_freq = top.row(0)[vc.columns.index(count_col)]
        print(f"\n{col}")
        print(f"  count={total:,}  unique={vc.height:,}  "
              f"mode='{mode_val}' (x{mode_freq:,})")
        for r in top.iter_rows(named=True):
            value = str(r[col])
            freq = r[count_col]
            disp = value if len(value) <= 60 else value[:57] + "..."
            print(f"    {freq:>8,}  {disp}")

    # --- Grouped by page_id ---
    df2 = df.with_columns(
        clean_numeric_expr("estimated_spend").alias("spend_num"),
        clean_numeric_expr("estimated_impressions").alias("impr_num"),
    )
    grp = (df2.group_by("page_id")
              .agg(
                  pl.len().alias("ads"),
                  pl.col("spend_num").sum().alias("total_spend"),
                  pl.col("spend_num").mean().alias("mean_spend"),
                  pl.col("impr_num").sum().alias("total_impr"),
              )
              .sort("ads", descending=True))

    print("\n" + "=" * 72)
    print("GROUPED BY page_id")
    print("=" * 72)
    print(f"Unique page_id groups: {grp.height:,}")
    print(f"\nTop {TOP_N} pages by ad count:")
    print(f"{'page_id (first 20 chars)':<24} {'ads':>8} {'total_spend':>14} "
          f"{'mean_spend':>12} {'total_impr':>14}")
    for r in grp.head(TOP_N).iter_rows(named=True):
        print(f"{r['page_id'][:20]:<24} {r['ads']:>8,} {r['total_spend']:>14,.0f} "
              f"{r['mean_spend']:>12,.1f} {r['total_impr']:>14,.0f}")

    # --- Grouped by (page_id, ad_id) ---
    n_pairs = df.group_by(["page_id", "ad_id"]).len().height
    print("\n" + "=" * 72)
    print("GROUPED BY (page_id, ad_id)")
    print("=" * 72)
    print(f"Unique (page_id, ad_id) groups: {n_pairs:,}")
    print(f"Total rows: {n_rows:,}")
    if n_pairs == n_rows:
        print("Each (page_id, ad_id) pair is unique - one row per ad.")
    else:
        print(f"{n_rows - n_pairs:,} rows share a (page_id, ad_id) pair.")


if __name__ == "__main__":
    main()
