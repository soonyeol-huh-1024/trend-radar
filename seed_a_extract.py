"""
A트랙(국내 셀러) 시드 추출: 네이버 위클리 키워드에서 "0 → 폭발 → (피크)" 국내 대박 키워드를 규칙으로 찾는다.

규칙 v1 (왁뿌볼이 상단에 오도록 교정):
  - 상품 카테고리 (NV_PRODUCT_CATS)
  - 베이스라인 0: 3년 미니시계열(6점, 반기) 앞 3점 평균 ≤ 피크의 BASE_RATIO
    → 전년 동기 봉우리가 있는 계절어는 자동 배제
  - 규모: 28주 내 월간검색 피크 ≥ MIN_PEAK
  - 폭발: s3y 피크 / max(앞3점 평균, 1) ≥ MIN_EXPLOSION
단계: rising(피크가 최근 4주 & 하락<10%) / peak(피크 최근 8주) / declining / dropped(리스트 이탈)

사용: python seed_a_extract.py
출력: data/seed_a_candidates.csv
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
NV_PRODUCT_CATS = {"화장품/미용", "식품", "생활/건강", "패션잡화", "패션의류", "출산/육아",
                   "스포츠/레저", "디지털/가전", "가구/인테리어"}
BASE_RATIO, MIN_PEAK, MIN_EXPLOSION = 0.05, 30_000, 20
# v2: 출시 이벤트·엔티티 배제 (셀러가 소싱할 수 없는 것). 단 '케이스' 등 액세서리는 유지.
ENTITY_LEAF = {"자급제폰", "게임타이틀", "CD/DVD콤보", "이색수집품", "기독교용품", "웨어러블 디바이스",
               "로봇청소기", "노트북", "태블릿PC", "TV", "콘솔게임기", "게임기"}
ENTITY_RE = r"갤럭시|아이폰|폴드\d|플립\d|로보락|아이패드|맥북|플레이스테이션|닌텐도|스위치2|쇼20\d\d|콘서트|시즌\d"
INTENT = ["만들기", "파는곳", "다이소", "추천", "가격", "후기", "효과", "부작용", "사용법", "레시피",
          "올리브영", "쿠팡", "구매", "정품", "차이", "뜻", "나무위키"]


def series(s: str) -> list[float]:
    try:
        v = json.loads(s) if isinstance(s, str) else None
        return [float(x or 0) for x in v] if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def profile(g: pd.DataFrame, wks: list[str]) -> dict:
    g = g.sort_values("week")
    last = g.iloc[-1]
    s3 = series(last["s3y"])
    base = float(np.mean(s3[:3])) if len(s3) >= 6 else np.nan
    pk3 = max(s3) if s3 else np.nan
    peak_i = int(g["search_cnt"].idxmax())
    peak_cnt, peak_week = float(g.loc[peak_i, "search_cnt"]), g.loc[peak_i, "week"]
    latest_cnt, latest_week = float(last["search_cnt"]), last["week"]
    decline = 1 - latest_cnt / peak_cnt if peak_cnt else np.nan
    if latest_week != wks[-1]:
        stage = "dropped"
    elif peak_week in wks[-4:] and decline < 0.10:
        stage = "rising"
    elif peak_week in wks[-8:]:
        stage = "peak"
    else:
        stage = "declining"
    return {
        "keyword": last["keyword"], "cat_top": last["cat_top"], "leaf": last["leaf"], "kw_type": last["kw_type"],
        "peak_cnt": int(peak_cnt), "peak_week": peak_week, "latest_cnt": int(latest_cnt), "latest_week": latest_week,
        "decline": round(decline, 2), "weeks_present": len(g), "first_week": g["week"].iloc[0],
        "s3y_base": round(base, 1) if base == base else np.nan, "s3y_peak": round(pk3, 1) if pk3 == pk3 else np.nan,
        "explosion": round(pk3 / max(base, 1.0), 1) if pk3 == pk3 and base == base else np.nan,
        "base_zero": bool(base == base and pk3 == pk3 and pk3 > 0 and base <= BASE_RATIO * pk3),
        "stage": stage, "s3y": last["s3y"],
    }


def main() -> None:
    nv = pd.read_csv(HERE / "data" / "cand_naver.csv")
    wks = sorted(nv["week"].unique())
    prof = pd.DataFrame([profile(g, wks) for _, g in nv.groupby("keyword")])
    prof["product_cat"] = prof["cat_top"].isin(NV_PRODUCT_CATS)
    prof["entity"] = prof["leaf"].isin(ENTITY_LEAF) | (
        prof["keyword"].str.contains(ENTITY_RE, regex=True) & ~prof["leaf"].fillna("").str.contains("케이스"))
    raw_hit = prof[prof["product_cat"] & prof["base_zero"] & (prof["peak_cnt"] >= MIN_PEAK)
                   & (prof["explosion"] >= MIN_EXPLOSION)]
    hit = raw_hit[~raw_hit["entity"]].copy()
    # 변종 클러스터: 자신을 부분문자열로 포함하는 가장 짧은 대박 키워드를 대표로
    names = sorted(hit["keyword"].tolist(), key=len)
    hit["cluster"] = hit["keyword"].map(lambda k: next((n for n in names if len(n) >= 2 and n in k), k))
    hit["rank_score"] = (hit["peak_cnt"].rank(pct=True) + hit["explosion"].rank(pct=True)).round(2)
    hit = hit.sort_values("rank_score", ascending=False).reset_index(drop=True)
    hit.to_csv(HERE / "data" / "seed_a_candidates.csv", index=False)
    rep = hit.drop_duplicates("cluster", keep="first").reset_index(drop=True)   # 클러스터 대표(최고 점수)

    pd.set_option("display.width", 230)
    cols = ["keyword", "cat_top", "leaf", "peak_cnt", "peak_week", "latest_cnt", "decline", "explosion",
            "s3y_base", "weeks_present", "stage"]
    print(f"키워드 {len(prof)}개 → 상품 {int(prof['product_cat'].sum())} → 베이스라인0 "
          f"{int((prof['product_cat'] & prof['base_zero']).sum())} → 규모≥{MIN_PEAK//1000}k & 폭발≥{MIN_EXPLOSION}배 "
          f"{len(raw_hit)} → 엔티티/출시 제외 {len(hit)} → 변종 클러스터 **{len(rep)}개**\n")
    print("=== 국내 대박 클러스터 상위 40 (대표 키워드, 규모·폭발 백분위 합) ===")
    sizes = hit.groupby("cluster").size()
    rep["variants"] = rep["cluster"].map(sizes)
    print(rep[cols + ["variants"]].head(40).to_string(index=False))
    w = rep.index[rep["keyword"] == "왁뿌볼"]
    print(f"\n왁뿌볼 순위: {int(w[0]) + 1 if len(w) else '미포함'} / {len(rep)}")
    ent = raw_hit[raw_hit["entity"]]
    print(f"엔티티/출시로 제외된 {len(ent)}개 예: {ent.sort_values('peak_cnt', ascending=False)['keyword'].head(12).tolist()}")

    now = rep[rep["stage"].isin(["rising", "peak"])].sort_values("peak_cnt", ascending=False)
    print(f"\n=== 지금 부상·피크 단계 (A트랙 현재 출력 미리보기, {len(now)}개) ===")
    print(now[cols].head(25).to_string(index=False))

    hit = rep   # 공통점은 클러스터 대표 기준
    print("\n=== 공통점 (클러스터 대표 기준) ===")
    print("단계:", dict(Counter(hit["stage"])))
    print("대분류 (대박 n / 풀 내 비율):")
    pool = prof[prof["product_cat"]]["cat_top"].value_counts()
    for c, n in hit["cat_top"].value_counts().items():
        print(f"  {c:<10} {n:>3}  ({n / pool.get(c, 1) * 100:.1f}% of {pool.get(c, 0)})")
    print("소분류 top:", dict(Counter(hit["leaf"]).most_common(12)))
    print("피크 월:", dict(sorted(Counter(hit["peak_week"].str[:7]).items())))
    print(f"수명: 첫등장→피크 중앙 {(pd.to_datetime(hit['peak_week']) - pd.to_datetime(hit['first_week'])).dt.days.median():.0f}일 | "
          f"하락 중앙 {hit['decline'].median():.0%} | 리스트 잔류 중앙 {hit['weeks_present'].median():.0f}주")
    dropped = hit[hit["stage"] == "dropped"]
    print(f"이탈 {len(dropped)}개 — 피크 후 이탈까지 중앙 "
          f"{(pd.to_datetime(dropped['latest_week']) - pd.to_datetime(dropped['peak_week'])).dt.days.median():.0f}일")

    try:
        from google.cloud import bigquery
        kws = hit["keyword"].tolist()
        rel = bigquery.Client(project="itemscout-data-358206").query(
            "SELECT keyword, ANY_VALUE(related_keywords) rel FROM `itemscout-data-358206.trend_data.keyword_growth` "
            "WHERE keyword IN UNNEST(@k) AND related_keywords != '[]' GROUP BY keyword",
            job_config=bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter("k", "STRING", kws)])
        ).to_dataframe()
        cnt = Counter()
        for r in rel["rel"]:
            toks = " ".join(json.loads(r))
            for w_ in INTENT:
                if w_ in toks:
                    cnt[w_] += 1
        print(f"연관어 의도어 (BQ 최근 8주 보유 {len(rel)}/{len(hit)}):", dict(cnt.most_common()))
    except Exception as e:  # BQ 미접근 시 생략
        print("연관어 의도어: 생략 —", str(e)[:80])


if __name__ == "__main__":
    main()
