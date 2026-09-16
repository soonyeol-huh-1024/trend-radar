"""
틱톡 확장 소스: Firestore tiktok_trend/raw_{hashtag}_{토요일} (해시태그 2,500+, 일별 viewsDelta 전체 히스토리)
→ 해시태그별 최신 스냅샷만 골라 주간(일~토, tiktok.ts aggregateToWeekly 와 동일) 합산.

+ BQ related_keywords(platform=tiktok) 로 "어느 분석 키워드의 이웃 해시태그인지" 매핑.

사용: python fetch_tiktok_raw.py [N_WEEKS]   (기본 40)
출력: data/cand_tiktok_raw.csv (hashtag, snapshot, week_end, views)
      data/cand_related_tiktok.csv (related_keyword, keyword, lang_code)
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from google.cloud import bigquery, firestore

HERE = Path(__file__).parent
DB = firestore.Client(project="gen-lang-client-0493835715", database="trend-checker")


def week_end(d: datetime) -> datetime:          # 해당 날짜가 속한 주의 토요일
    return d + timedelta(days=(5 - d.weekday()) % 7)


def parse(doc: dict, n_weeks: int) -> list[tuple[str, int]]:
    try:
        items = json.loads(doc.get("trendDataJson") or "[]")
    except json.JSONDecodeError:
        return []
    wk = defaultdict(int)
    last = None
    for it in items:
        ds = (it.get("day") or it.get("date") or "")[:10]
        if not ds:
            continue
        d = datetime.fromisoformat(ds)
        last = max(last, d) if last else d
        wk[week_end(d)] += int(it.get("viewsDelta") or 0)
    if last is None:
        return []
    if last.weekday() != 5:                     # 마지막 미완성 주 제거 (ts 정합)
        wk.pop(week_end(last), None)
    return sorted(((k.date().isoformat(), v) for k, v in wk.items()))[-n_weeks:]


def main() -> None:
    n_weeks = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    refs = [r for r in DB.collection("tiktok_trend").list_documents() if r.id.startswith("raw_")]
    latest: dict[str, tuple[str, object]] = {}
    for r in refs:
        tag, sat = r.id[4:].rsplit("_", 1)
        if tag not in latest or sat > latest[tag][0]:
            latest[tag] = (sat, r)
    print(f"raw_ 문서 {len(refs)} → 고유 해시태그 {len(latest)}")

    rows = []
    picked = [v[1] for v in latest.values()]
    for i in range(0, len(picked), 300):
        for snap in DB.get_all(picked[i:i + 300]):
            d = snap.to_dict() or {}
            tag = snap.id[4:].rsplit("_", 1)[0]
            for wkend, views in parse(d, n_weeks):
                rows.append({"hashtag": tag, "snapshot": d.get("lastSaturday"), "week_end": wkend, "views": views})
        print(f"  {min(i + 300, len(picked))}/{len(picked)} 처리, rows={len(rows)}")
    df = pd.DataFrame(rows)
    out = HERE / "data"
    df.to_csv(out / "cand_tiktok_raw.csv", index=False)
    print(f"저장 cand_tiktok_raw.csv rows={len(df)} hashtags={df['hashtag'].nunique()} "
          f"weeks={df['week_end'].min()}~{df['week_end'].max()}")

    rel = bigquery.Client(project="itemscout-data-358206").query("""
        SELECT DISTINCT related_keyword, keyword, lang_code
        FROM `itemscout-data-358206.trend_data.related_keywords` WHERE platform = 'tiktok'
    """).to_dataframe()
    rel.to_csv(out / "cand_related_tiktok.csv", index=False)
    print(f"저장 cand_related_tiktok.csv rows={len(rel)}")


if __name__ == "__main__":
    main()
