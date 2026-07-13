
import csv
import math
import sys
from collections import Counter, defaultdict

MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-"}
SAMPLE_SIZE = 2000        # rows used to infer each column's type
TOP_N = 15                # how many groups to display

# The two numeric columns that are meaningful to aggregate per group.
GROUP_METRICS = ["estimated_spend", "estimated_impressions"]


def is_missing(value):
    return value is None or value.strip().lower() in MISSING_TOKENS


def try_number(value):
    if is_missing(value):
        return None
    cleaned = value.strip().replace("$", "").replace(",", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def infer_types(path, headers):
    """Read the first SAMPLE_SIZE rows and classify each column."""
    samples = {h: [] for h in headers}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= SAMPLE_SIZE:
                break
            for h in headers:
                v = row.get(h)
                if not is_missing(v):
                    samples[h].append(v)

    types = {}
    for h in headers:
        vals = samples[h]
        if not vals:
            types[h] = "empty"
        else:
            numeric = sum(1 for v in vals if try_number(v) is not None)
            types[h] = "numeric" if numeric / len(vals) >= 0.8 else "categorical"
    return types


def stddev(nums, mean):
    n = len(nums)
    if n < 2:
        return 0.0
    return math.sqrt(sum((x - mean) ** 2 for x in nums) / (n - 1))


def median(sorted_nums):
    n = len(sorted_nums)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return sorted_nums[mid]
    return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2


def fmt(x):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:,.4f}"
    return f"{x:,}" if isinstance(x, int) else str(x)


def main():
    if len(sys.argv) != 2:
        print("Usage: python pure_python_stats.py path/to/dataset.csv")
        sys.exit(1)
    path = sys.argv[1]

    # --- Pass 0: headers + type inference from a sample ---
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        headers = next(csv.reader(f))
    types = infer_types(path, headers)

    numeric_cols = [h for h in headers if types[h] == "numeric"]
    categorical_cols = [h for h in headers if types[h] != "numeric"]

    # Accumulators
    numeric_values = {h: [] for h in numeric_cols}   
    cat_counters = {h: Counter() for h in categorical_cols}
    missing_counts = {h: 0 for h in headers}
    row_count = 0

    # Grouped accumulators: {group_key: {"count": n, "estimated_spend": sum, ...}}
    by_page = defaultdict(lambda: {"count": 0,
                                   "estimated_spend": 0.0,
                                   "estimated_impressions": 0.0})
    page_ad_pairs = set()

    # --- Single streaming pass ---
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_count += 1
            for h in headers:
                v = row.get(h)
                if is_missing(v):
                    missing_counts[h] += 1
                    continue
                if types[h] == "numeric":
                    num = try_number(v)
                    if num is not None:
                        numeric_values[h].append(num)
                else:
                    cat_counters[h][v.strip()] += 1

            # Grouped by page_id
            pid = row.get("page_id")
            if pid is not None:
                g = by_page[pid]
                g["count"] += 1
                for m in GROUP_METRICS:
                    num = try_number(row.get(m, ""))
                    if num is not None:
                        g[m] += num
            # Grouped by (page_id, ad_id)
            page_ad_pairs.add((pid, row.get("ad_id")))

    # --- Output: dataset level ---
    print("=" * 72)
    print(f"DATASET: {path}")
    print(f"Rows: {row_count:,}    Columns: {len(headers)}")
    print("=" * 72)

    print("\nCOLUMN OVERVIEW (missing | type)")
    print("-" * 72)
    for h in headers:
        pct = (missing_counts[h] / row_count * 100) if row_count else 0
        print(f"{h:<42} {missing_counts[h]:>8,} ({pct:5.1f}%)  {types[h]}")

    print("\nNUMERIC COLUMNS (dataset level)")
    print("-" * 72)
    for h in numeric_cols:
        nums = numeric_values[h]
        if not nums:
            continue
        mean = sum(nums) / len(nums)
        s = sorted(nums)
        print(f"\n{h}")
        print(f"  count={len(nums):,}  mean={fmt(mean)}  median={fmt(median(s))}")
        print(f"  min={fmt(min(nums))}  max={fmt(max(nums))}  std={fmt(stddev(nums, mean))}")

    print("\nCATEGORICAL COLUMNS (dataset level)")
    print("-" * 72)
    for h in categorical_cols:
        c = cat_counters[h]
        total = sum(c.values())
        if total == 0:
            continue
        mode, freq = c.most_common(1)[0]
        print(f"\n{h}")
        print(f"  count={total:,}  unique={len(c):,}  mode='{mode}' (x{freq:,})")
        for value, f_ in c.most_common(5):
            disp = value if len(value) <= 60 else value[:57] + "..."
            print(f"    {f_:>8,}  {disp}")

    # --- Output: grouped by page_id ---
    print("\n" + "=" * 72)
    print("GROUPED BY page_id")
    print("=" * 72)
    print(f"Unique page_id groups: {len(by_page):,}")
    top_pages = sorted(by_page.items(), key=lambda kv: kv[1]["count"], reverse=True)[:TOP_N]
    print(f"\nTop {TOP_N} pages by ad count:")
    print(f"{'page_id (first 20 chars)':<24} {'ads':>8} {'total_spend':>14} "
          f"{'mean_spend':>12} {'total_impr':>14}")
    for pid, g in top_pages:
        mean_spend = g["estimated_spend"] / g["count"] if g["count"] else 0
        print(f"{pid[:20]:<24} {g['count']:>8,} {g['estimated_spend']:>14,.0f} "
              f"{mean_spend:>12,.1f} {g['estimated_impressions']:>14,.0f}")

    # --- Output: grouped by (page_id, ad_id) ---
    print("\n" + "=" * 72)
    print("GROUPED BY (page_id, ad_id)")
    print("=" * 72)
    print(f"Unique (page_id, ad_id) groups: {len(page_ad_pairs):,}")
    print(f"Total rows: {row_count:,}")
    if len(page_ad_pairs) == row_count:
        print("Each (page_id, ad_id) pair is unique - one row per ad.")
    else:
        print(f"{row_count - len(page_ad_pairs):,} rows share a (page_id, ad_id) pair.")


if __name__ == "__main__":
    main()
