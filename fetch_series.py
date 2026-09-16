"""
시드 키워드의 주간 tt/gg/az 시계열을 BigQuery trend_daily에서 추출.

trend_daily는 같은 (keyword, lang_code, date)가 분석 회차(analyzed_date)마다
중복 적재되므로, 최신 analyzed_date 행만 남긴다.

사용: python fetch_series.py [LANG] [--all]   (기본 US; LANG=ALL 이면 전 국가)
      --all: 시드가 아닌 trend_daily 의 모든 키워드
출력: data/series_{LANG}.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

PROJECT = "itemscout-data-358206"
TABLE = f"`{PROJECT}.trend_data.trend_daily`"
HERE = Path(__file__).parent

QUERY = f"""
SELECT keyword, lang_code, date, tt, gg, az, analyzed_date
FROM {TABLE}
WHERE (@all OR keyword IN UNNEST(@keywords))
  AND (@lang = "ALL" OR lang_code = @lang)
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY keyword, lang_code, date ORDER BY analyzed_date DESC
) = 1
ORDER BY keyword, date
"""


def load_seeds() -> list[str]:
    cfg = json.loads((HERE / "seed_keywords.json").read_text())
    return [s["keyword"] for s in cfg["seeds"]]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    lang = args[0].upper() if args else "US"
    use_all = "--all" in sys.argv
    keywords = load_seeds()
    client = bigquery.Client(project=PROJECT)
    job = client.query(
        QUERY,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("keywords", "STRING", keywords),
                bigquery.ScalarQueryParameter("lang", "STRING", lang),
                bigquery.ScalarQueryParameter("all", "BOOL", use_all),
            ]
        ),
    )
    df: pd.DataFrame = job.to_dataframe()
    out = HERE / "data"
    out.mkdir(exist_ok=True)
    path = out / f"series_{lang}.csv"
    df.to_csv(path, index=False)

    combos = df.groupby(["keyword", "lang_code"]).ngroups
    print(f"lang={lang} all={use_all} rows={len(df)} keywords={df['keyword'].nunique()} combos={combos}")
    if not use_all:
        summary = (
            df.groupby("keyword")
            .agg(weeks=("date", "count"),
                 first=("date", "min"), last=("date", "max"),
                 tt_weeks=("tt", lambda s: int((s > 0).sum())),
                 az_weeks=("az", lambda s: int((s > 0).sum())),
                 analyzed=("analyzed_date", "max"))
        )
        print(summary.to_string())
        missing = set(keywords) - set(df["keyword"])
        if missing:
            print(f"\n[경고] {lang}에 없는 시드: {sorted(missing)}")
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
