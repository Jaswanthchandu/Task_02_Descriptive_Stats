# Task_02_Descriptive_Stats

> Note: The statistics scripts were developed with AI assistance; the analysis, validation, and findings are my own.

Descriptive statistics on a 2024 U.S. Facebook/Instagram political-ads dataset,
computed three independent ways — pure standard-library Python, pandas, and
Polars — with dataset-level and grouped analysis, and verified to agree.

## Dataset

Source: [2024 Facebook Political Ads — Milestone A (Google Drive)](https://drive.google.com/file/d/1UPo11lH2Mlk2cnLtjv8P9XqlKitms-gp/view?usp=sharing)

File used: `2024_fb_ads_president_scored_anon.csv` (246,745 rows x 41 columns).
This is a **different file** from Task 1 — similar subject, different schema. The
dataset is **not** included in this repository. Download it from the link above,
place the CSV locally, and pass its path to the scripts.

## How to run

```bash
pip install -r requirements.txt
python pure_python_stats.py path\to\2024_fb_ads_president_scored_anon.csv > pure_out.txt
python pandas_stats.py      path\to\2024_fb_ads_president_scored_anon.csv > pandas_out.txt
python polars_stats.py      path\to\2024_fb_ads_president_scored_anon.csv > polars_out.txt
```

Then compare the three output files — the numeric stats and grouped tables match.

## What each script does

All three compute the same thing three ways:
- **Dataset level** — per column: count, mean, min, max, sample std, median
  (numeric); count, unique, mode + frequency, top 5 (categorical). Plus row/column
  counts, missing values per column, and inferred type per column.
- **Grouped** — by `page_id` (ad count, total/mean spend, total impressions per
  page; top pages shown) and by `page_id + ad_id`.

- `pure_python_stats.py` — standard library only (`csv`, `math`, `collections`);
  streaming single pass with running counters to stay memory-light on the ~500 MB file.
- `pandas_stats.py` — pandas (`groupby`, `value_counts`, `nunique`).
- `polars_stats.py` — Polars (expression-based, `group_by` + `agg`); reads all
  columns as strings then casts, so type handling matches the other two.

All three use sample standard deviation (n − 1).

## Findings

One of the biggest differences between this dataset and the one from Task 1 is that the estimated spend, estimated impressions, and estimated audience size are now stored as actual numbers instead of ranges. This makes it possible to perform real numerical analysis instead of treating these columns as categories.

Looking at the spend data, I noticed that the average estimated spend is $1,061, while the median is only $49. The maximum spend is $474,999. The large gap between the mean and median shows that the data is highly right-skewed. Most advertisements spent relatively small amounts, while a small number of ads had very large budgets that increased the overall average. The same pattern appears in the impressions data. The average number of impressions is 45,601, but the median is only 3,499. The estimated audience size also shows a similar trend, with an average of about 556,000 people compared to a median of 300,000.

The dataset contains 246,745 advertisements across 41 columns, collected from Facebook and Instagram during the 2024 U.S. presidential election. Unlike the previous dataset, this version has a different schema. For example, the illuminating fields now use a suffix instead of a prefix, the page_name column has been removed, and new columns such as delivery_by_region, demographic_distribution, freefair_illuminating, and fraud_illuminating have been added.

Since this dataset includes actual spending values, I was also able to compare pages based on both the number of ads and the amount of money spent. After grouping the data by page_id, there were 4,475 unique pages. The most active page published 55,503 ads, spent about $82.8 million, and generated nearly 3 billion impressions. The second-largest page published 23,988 ads with a total spend of $19.6 million, while the third-largest page published 14,822 ads but spent $26.4 million. Even though the third page published fewer advertisements than the second, it spent much more money on each ad, with an average spend of about $1,779 compared to $817. This shows that ranking pages by advertisement count and ranking them by spending can produce different results. Looking at the bylines, HARRIS FOR PRESIDENT and HARRIS VICTORY FUND together account for more than 82,000 advertisements, while DONALD J. TRUMP FOR PRESIDENT 2024, INC. appears in 15,112 ads and BIDEN VICTORY FUND appears in 15,539 ads.

The dataset also contains 26 binary illuminating flags that describe the content of each advertisement. Since these columns contain only 0 or 1, the average value represents the percentage of ads with that characteristic. About 57.3% of advertisements include a call to action, while 54.9% are classified as advocacy messages. Issue-related content appears in 38.2% of ads, and 27.2% contain attack messaging. Among the call-to-action categories, fundraising (22.9%) is the most common, followed by voting (14.4%) and engagement (12.5%). The economy (12.2%) is the most common topic, followed by health (10.9%), social and cultural issues (10.6%), and women's issues (8.1%). Foreign policy, military, technology, and LGBTQ topics each appear in less than 1% of advertisements. Around 18.8% of ads are flagged for incivility, 7.2% for scam-like content, while the two new flags appear only rarely, with freefair_illuminating in 0.6% of ads and fraud_illuminating in 0.3%.

The timing of the advertisements also follows the expected election pattern. Advertisement creation dates increase sharply during the last week of October, with October 27 recording the highest number of newly created ads (8,619). Almost every advertisement (99.9%) used U.S. dollars, and around 87% were shown on both Facebook and Instagram instead of only one platform.

Finally, I looked at the two new complex columns, delivery_by_region and demographic_distribution. These columns contain nested dictionary values rather than simple text or numbers. They have around 141,000 and 216,000 unique values, which means that most records contain different information. The most common value in delivery_by_region is simply an empty dictionary ({}), which appears in 30,989 advertisements. For this assignment, these columns were treated as categorical text because analyzing them properly would require parsing the nested dictionaries first. I also found that every page_id and ad_id combination appears only once, meaning there is one row per advertisement. Because of this, calculating descriptive statistics for each page-ad pair would not provide any meaningful insights.

## Comparison of the three approaches

All three implementations, pure Python, pandas, and Polars, produced the same overall results. The descriptive statistics for the dataset matched across all three programs, and the grouped analysis by page_id produced the same rankings for advertisement count, total spend, and impressions. The pandas and Polars output files were identical, while the pure Python version only differed slightly in formatting. All three implementations also calculated the sample standard deviation using n − 1, which confirms that they were performing the same statistical calculations.

Writing the analysis in pure Python required the most work because everything had to be implemented manually. I had to define which values should be treated as missing data, create an 80% parsing rule to determine whether a column should be treated as numerical, and write my own grouping logic using dictionaries keyed by page_id. Since some columns contain very large nested dictionary values, I also had to think about memory usage. Instead of loading everything into memory, I used a streaming approach together with Counter objects for categorical columns, which kept the program more efficient.

The pandas implementation was much simpler because many operations are built into the library. Functions such as .groupby() and .describe() made the code shorter and easier to read, although I still had to specify the missing-value tokens using na_values so that the results matched the other implementations.

Using Polars was a different experience because it follows an expression-based style instead of the indexing style used by pandas. At first, writing expressions like pl.col() and creating lists of aggregation expressions felt a little unusual because I was used to the pandas syntax. Polars also uses stricter data types, so I chose to read every column as a string first and then explicitly cast the columns to the correct types. Although this required a little more planning, it made the data types much clearer. Once I became familiar with the syntax, the code was easy to follow, and I also noticed that Polars processed the data very quickly.

For this assignment, I think pandas is easier for someone learning data analysis because it has a simpler syntax and a much larger community with plenty of tutorials and examples. However, after using Polars, I can see why it is becoming popular for working with larger datasets because of its speed and strict handling of data types.

One design decision in the grouped analysis was to summarize statistics at the page level instead of producing descriptive statistics for every column within each of the 4,475 page groups. Reporting full descriptive statistics for every column in every group would create thousands of pages of output and make the important results difficult to find. Instead, grouping by page and reporting advertisement count, total spend, and total impressions highlights the information that is actually useful.

Compared to Task 1, the most valuable new insight comes from the availability of real spending values. Because the spend column now contains actual numbers instead of ranges, it is possible to see that the mean spend ($1,061) is much larger than the median spend ($49). This clearly shows a right-skewed distribution, where most advertisements have relatively small budgets while a small number of expensive advertisements account for a large share of the total spending. This was something that could not be observed in the previous dataset because spending was only available as bucketed ranges.

## Reproducibility

Clone the repo, install `requirements.txt`, download the dataset to a local path,
and run the three commands above. Each script prints to stdout; redirect to a file
to save the output.
