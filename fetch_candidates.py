"""
후보 유니버스 수집: Firestore weekly_keywords / tiktok_weekly / amazon_weekly → long CSV.

- weekly_keywords/{월요일}_chunk_N   : 네이버 주간 키워드 4,708개 (KR 조기 신호)
- tiktok_weekly/{us|kr}_{수요일}_7d_chunk_0 : 해시태그 100개, videoViews 는 누적
- amazon_weekly/{us|jp}_{금요일}      : searchRanking/salesRanking top-100

사용: python fetch_candidates.py [N_WEEKS] [--only naver|tiktok|amazon]   (기본 26, 전체)
출력: data/cand_naver.csv (1y/3y 미니 시계열 JSON 포함), cand_tiktok.csv, cand_amazon.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd
from google.cloud import firestore

HERE = Path(__file__).parent
DB = firestore.Client(project="gen-lang-client-0493835715", database="trend-checker")


def weeks(coll: str, idx_doc: str, n: int) -> list[str]:
    d = DB.collection(coll).document(idx_doc).get().to_dict() or {}
    return sorted(d.get("weeks", []))[-n:]


def fetch_naver(n: int) -> pd.DataFrame:
    rows = []
    for wk in weeks("weekly_keywords", "weeks", n):
        meta = DB.collection("weekly_keywords").document(wk).get().to_dict() or {}
        for c in range(int(meta.get("chunks", 0))):
            doc = DB.collection("weekly_keywords").document(f"{wk}_chunk_{c}").get().to_dict() or {}
            for k in doc.get("keywords", []):
                cat = k.get("category") or ""
                rows.append({
                    "week": wk, "keyword": k.get("keyword"),
                    "cat_top": cat.split(" > ")[0], "leaf": k.get("leafCategory"),
                    "kw_type": k.get("keywordType"), "search_cnt": k.get("searchCnt"),
                    "mom": k.get("mom"), "qoq": k.get("qoq"), "yoy": k.get("yoy"),
                    "ath": k.get("allTimeHigh"), "growth1m": k.get("growth1m"),
                    "growth3m": k.get("growth3m"),
                    "s1y": json.dumps(k.get("search1yMini"), ensure_ascii=False),
                    "s3y": json.dumps(k.get("search3yMini"), ensure_ascii=False),
                })
        print(f"  naver {wk}: 누적 {len(rows)}")
    return pd.DataFrame(rows)


def fetch_tiktok(n: int) -> pd.DataFrame:
    rows = []
    for cc in ("us", "kr"):
        for wk in weeks("tiktok_weekly", f"{cc}_weeks", n):
            doc = DB.collection("tiktok_weekly").document(f"{cc}_{wk}_7d_chunk_0").get().to_dict()
            if not doc:
                doc = DB.collection("tiktok_weekly").document(f"{cc}_{wk}_30d_chunk_0").get().to_dict() or {}
            for k in doc.get("keywords", []):
                rows.append({
                    "week": wk, "cc": cc, "hashtag": k.get("hashtag"),
                    "category": k.get("category"), "views_total": k.get("videoViews"),
                    "publish_cnt": k.get("publishCnt"), "is_new": bool(k.get("isNew")),
                })
        print(f"  tiktok {cc}: 누적 {len(rows)}")
    return pd.DataFrame(rows)


def fetch_amazon(n: int) -> pd.DataFrame:
    rows = []
    for cc in ("us", "jp"):
        for wk in weeks("amazon_weekly", f"{cc}_weeks", n):
            doc = DB.collection("amazon_weekly").document(f"{cc}_{wk}").get().to_dict() or {}
            for lst in ("searchRanking", "salesRanking"):
                for k in doc.get(lst, []):
                    rows.append({
                        "week": wk, "cc": cc, "list": lst[:-7],
                        "keyword": k.get("keyword"), "category": k.get("category"),
                        "search_cnt": k.get("search_cnt"), "sales": k.get("sales"),
                        "revenue": k.get("revenue"), "price": k.get("price"), "bsr": k.get("bsr"),
                        "is_new_week": bool(k.get("isNewWeek")),
                        "is_new_month": bool(k.get("isNewMonth")),
                    })
        print(f"  amazon {cc}: 누적 {len(rows)}")
    return pd.DataFrame(rows)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 26
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    out = HERE / "data"
    out.mkdir(exist_ok=True)
    for name, fn in (("naver", fetch_naver), ("tiktok", fetch_tiktok), ("amazon", fetch_amazon)):
        if only and name != only:
            continue
        df = fn(n)
        df.to_csv(out / f"cand_{name}.csv", index=False)
        print(f"저장 cand_{name}.csv rows={len(df)} weeks={df['week'].nunique()}\n")


if __name__ == "__main__":
    main()
