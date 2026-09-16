"""
BigQuery amazon_weekly(일별 us 1,740 / jp 1,218 키워드) → 주간 집계 CSV.

Firestore amazon_weekly 는 top-100 요약이라 "부재" 판정이 약하다. BQ 원본은
검색 1.8천 + 판매 6.4천(US) 키워드 유니버스라 부재 = 정말 조용, 순위권 밖의
검색량 상승(rising)도 잡을 수 있다. (기간은 2026-06-18~ 로 짧음)

사용: python fetch_amazon_bq.py
출력: data/cand_amazon_bq.csv  (country, analysis_type, keyword, category, week, days, avg_search, avg_sales, avg_price, min_bsr)
"""
from pathlib import Path

from google.cloud import bigquery

HERE = Path(__file__).parent
PROJECT = "itemscout-data-358206"
QUERY = """
SELECT country, analysis_type, keyword, ANY_VALUE(category) AS category,
  DATE_TRUNC(date, WEEK(MONDAY)) AS week, COUNT(DISTINCT date) AS days,
  ROUND(AVG(search_cnt)) AS avg_search, ROUND(AVG(sales)) AS avg_sales,
  ROUND(AVG(price), 2) AS avg_price, MIN(bsr) AS min_bsr
FROM `itemscout-data-358206.trend_data.amazon_weekly`
GROUP BY country, analysis_type, keyword, week
ORDER BY country, keyword, week
"""


def main() -> None:
    df = bigquery.Client(project=PROJECT).query(QUERY).to_dataframe()
    df["list"] = df["analysis_type"].map(lambda s: "search" if s.startswith("impression") else "sales")
    out = HERE / "data" / "cand_amazon_bq.csv"
    df.to_csv(out, index=False)
    print(f"rows={len(df)} weeks={df['week'].nunique()} ({df['week'].min()}~{df['week'].max()})")
    print(df.groupby(["country", "list"])["keyword"].nunique().rename("distinct_kw").to_string())
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
