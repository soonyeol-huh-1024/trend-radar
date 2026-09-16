"""
"아직 안 뜬" 후보 스크리닝: 시그니처(hit 공통점)를 세 소스에 적용.

시그니처 → 규칙
  ① az 베이스라인 낮음  → 아마존 top-100 에 부재(absent) 또는 최근 8주 내 첫 진입(new)
  ② 틱톡 스파이크(+구글) → 해시태그 주간 신규조회수(누적 차분)가 직전 8주 중앙값의 SPIKE 배 이상
  ③ 상품 카테고리       → 틱톡 category / 네이버 대분류 화이트리스트 (+ 이후 의미 주석)
  ⑤ 다국가            → us·kr 틱톡 동시 출현 가점
  KR 조기 신호         → 네이버 '1주/1달 전에 없던' 또는 '1년전 없던'+ATH, 상품 카테고리

사용: python screen.py
출력: data/screen_tiktok.csv, screen_naver.csv, screen_amazon_new.csv
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
SPIKE, BASE_W, RECENT_W, NEW_W = 1.5, 8, 4, 8
TT_PRODUCT_CATS = {"shopping", "beauty", "fashion", "food", "health", "home"}
TT_GENERIC = {"asmr", "makeup", "makeuptutorial", "grwm", "ootd", "outfitinspo", "food", "foodie",
              "mukbang", "diy", "hair", "hairtok", "skincare", "fashion", "beauty", "cooking",
              "recipe", "halloween", "christmas", "kitty", "shopping", "haul", "unboxing", "fyp"}
NV_PRODUCT_CATS = {"화장품/미용", "식품", "생활/건강", "패션잡화", "패션의류", "출산/육아",
                   "스포츠/레저", "디지털/가전", "가구/인테리어"}
NV_MIN_SEARCH = 3000
AZ_MEDIA_CATS = {"Movies & TV", "Books", "CDs & Vinyl", "Video Games", "Digital Music", "Kindle Store",
                 "Software", "Apps & Games", "Audible Books & Originals", "Prime Video", "Magazine Subscriptions",
                 "ゲーム", "本", "ミュージック", "DVD", "デジタルミュージック", "Kindleストア", "PCソフト", "雑誌"}
AZ_MIN_SEARCH = 5000


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-zㄱ-힝぀-ヿ一-鿿]", "", str(s).lower())


def amazon_status(am: pd.DataFrame) -> pd.DataFrame:
    """Firestore top-100 (130주) 기준 (cc, norm) 별 상태 — 시드 소급검증용."""
    am = am.assign(n=am["keyword"].map(norm))
    wks = sorted(am["week"].unique())
    recent = set(wks[-NEW_W:])
    g = am.groupby(["cc", "n"])
    st = pd.DataFrame({
        "keyword": g["keyword"].first(), "weeks_present": g["week"].nunique(),
        "first_week": g["week"].min(), "last_week": g["week"].max(),
        "max_search": g["search_cnt"].max(), "category": g["category"].first(),
        "new_recent": g["is_new_week"].any(),
    }).reset_index()
    st["az_status"] = np.where(st["first_week"].isin(recent), "new",
                               np.where(st["weeks_present"] >= NEW_W, "established", "fading"))
    return st


def amazon_status_bq(ab: pd.DataFrame) -> pd.DataFrame:
    """BQ 원본(일 1,740/1,218 키워드, 2026-06-18~) 기준 현재 스크리닝용 상태.
    established = 창 시작 2주 내 존재 / new = 최근 NEW_W/2 주 내 첫 등장 / rising = 검색량 최근2주/초기2주 ≥ 1.5"""
    ab = ab.assign(n=ab["keyword"].map(norm), week=pd.to_datetime(ab["week"]))
    wks = sorted(ab["week"].unique())
    start2, recent = set(wks[:2]), set(wks[-(NEW_W // 2):])
    g = ab.groupby(["country", "n"])
    st = pd.DataFrame({
        "keyword": g["keyword"].first(), "category": g["category"].first(),
        "weeks_present": g["week"].nunique(), "first_week": g["week"].min(), "last_week": g["week"].max(),
        "max_search": g["avg_search"].max(),
    }).reset_index().rename(columns={"country": "cc"})
    sr = ab[ab["list"] == "search"].sort_values("week")
    gs = sr.groupby(["country", "n"])["avg_search"]
    growth = (gs.apply(lambda s: s.iloc[-2:].mean() / max(s.iloc[:2].mean(), 1) if len(s) >= 4 else np.nan)
              .rename("az_growth").reset_index().rename(columns={"country": "cc"}))
    st = st.merge(growth, on=["cc", "n"], how="left")
    st["az_status"] = np.where(st["first_week"].isin(start2), "established",
                               np.where(st["first_week"].isin(recent), "new", "mid"))
    st["rising"] = st["az_growth"] >= 1.5
    return st


def screen_tiktok(tt: pd.DataFrame, az: pd.DataFrame) -> pd.DataFrame:
    tt = tt.sort_values(["cc", "hashtag", "week"])
    tt["delta"] = tt.groupby(["cc", "hashtag"])["views_total"].diff()
    rows = []
    for (cc, h), g in tt.groupby(["cc", "hashtag"]):
        d = g["delta"].dropna()
        if len(d) == 0:
            continue
        rec = d.iloc[-RECENT_W:].mean()
        base = d.iloc[-(RECENT_W + BASE_W):-RECENT_W].median() if len(d) > RECENT_W else np.nan
        spike = rec / base if base and base > 0 else np.nan
        rows.append({"cc": cc, "hashtag": h, "category": g["category"].iloc[-1],
                     "weeks_present": len(g), "first_week": g["week"].min(),
                     "recent_views_wk": round(rec / 1e6, 1), "spike": round(spike, 2) if spike == spike else np.nan,
                     "is_new": bool(g["is_new"].any())})
    r = pd.DataFrame(rows)
    r["n"] = r["hashtag"].map(norm)
    r["generic"] = r["n"].isin(TT_GENERIC)
    r["product_cat"] = r["category"].isin(TT_PRODUCT_CATS)
    both = r.groupby("n")["cc"].nunique()
    r["multi_cc"] = r["n"].map(both) >= 2
    us_az = az[az["cc"] == "us"].drop_duplicates("n").set_index("n")
    r["az_status"] = r["n"].map(us_az["az_status"]).fillna("absent")
    r["az_rising"] = r["n"].map(us_az["rising"]).fillna(False).astype(bool)
    wks = sorted(tt["week"].unique())
    r["tt_lit"] = (r["spike"] >= SPIKE) | r["first_week"].isin(wks[-NEW_W:])
    r["score"] = (3 * r["tt_lit"] + 2 * (r["az_status"] == "absent") + 1 * (r["az_status"] == "new")
                  + 1 * r["az_rising"] - 3 * (r["az_status"] == "established") + 1 * r["multi_cc"]
                  + 1 * r["product_cat"] - 4 * r["generic"])
    return r.sort_values("score", ascending=False)


def screen_tiktok_raw(raw: pd.DataFrame, az: pd.DataFrame, rel: pd.DataFrame) -> pd.DataFrame:
    """확장 소스(raw_ 해시태그 2,500+, 주간 viewsDelta 합) 스크리닝. 규칙은 screen_tiktok 과 동일."""
    raw = raw.sort_values(["hashtag", "week_end"])
    wks = sorted(raw["week_end"].unique())
    rows = []
    for h, g in raw.groupby("hashtag"):
        v = g.set_index("week_end")["views"].reindex(wks[-(RECENT_W + BASE_W):], fill_value=0)
        rec, base = v.iloc[-RECENT_W:].mean(), v.iloc[:BASE_W].median()
        active = g[g["views"] > 0]["week_end"]
        rows.append({"hashtag": h, "spike": round(rec / base, 2) if base > 0 else np.nan,
                     "recent_views_wk": round(rec / 1e6, 2), "base_views_wk": round(base / 1e6, 2),
                     "first_active": active.min() if len(active) else None,
                     "weeks_active": int(len(active)), "snapshot": g["snapshot"].iloc[-1]})
    r = pd.DataFrame(rows)
    r["n"] = r["hashtag"].map(norm)
    r["generic"] = r["n"].isin(TT_GENERIC) | r["n"].str.contains("partner|ambassador|affiliate|sponsored")
    r["is_new"] = r["first_active"].isin(wks[-NEW_W:]) & (r["recent_views_wk"] >= 0.1)
    r["tt_lit"] = (r["spike"] >= SPIKE) & (r["recent_views_wk"] >= 0.1) | r["is_new"]
    us_az = az[az["cc"] == "us"].drop_duplicates("n").set_index("n")
    r["az_status"] = r["n"].map(us_az["az_status"]).fillna("absent")   # BQ 유니버스 — labubu 도 '부재'라 약한 근거
    r["az_rising"] = r["n"].map(us_az["rising"]).fillna(False).astype(bool)
    src = rel.groupby(rel["related_keyword"].map(norm))["keyword"].agg(lambda s: ",".join(sorted(set(s))[:3]))
    r["source_kw"] = r["n"].map(src).fillna("")
    # 원천 키워드가 분석된 경우 우리 trend_daily 의 US az 레벨(hit_score az_late)을 우선 근거로 사용
    hs = pd.read_csv(HERE / "data" / "hit_score_ALL.csv")
    us_lvl = hs[hs["lang"] == "US"].set_index("keyword")["az_late"]
    r["src_az_us"] = r["source_kw"].str.split(",").str[0].map(us_lvl)
    r["src_az_hot"] = r["src_az_us"] >= 20
    # 원천 키워드가 엔티티(스포츠리그·K-pop·레스토랑·서비스)면 그 이웃 태그도 상품 신호가 아님 → 강등
    a = pd.read_csv(HERE / "keyword_attrs.csv", dtype=str).fillna("")
    a = a[a["alias_of"] == ""].set_index("keyword")
    src0 = r["source_kw"].str.split(",").str[0]
    r["src_type"] = src0.map(a["type"]).fillna("?")
    r["src_entity"] = r["src_type"].isin(["entity", "restaurant", "service", "concept"]) | \
        src0.map(a["category"]).isin(["sports_league", "kpop", "entertainment"])
    r["score"] = (3 * r["tt_lit"] + 1 * (r["az_status"] == "absent") + 1 * (r["az_status"] == "new")
                  + 1 * r["az_rising"] - 3 * (r["az_status"] == "established") - 2 * r["src_az_hot"]
                  - 4 * r["generic"] - 4 * r["src_entity"]
                  + np.clip(np.log10(r["recent_views_wk"].clip(lower=0.01) * 100) / 2, 0, 2))
    return r.sort_values(["score", "recent_views_wk"], ascending=False)


def screen_naver(nv: pd.DataFrame) -> pd.DataFrame:
    wks = sorted(nv["week"].unique())
    latest = nv[nv["week"] == wks[-1]].copy()
    pres = nv.groupby("keyword")["week"].nunique()
    first = nv.groupby("keyword")["week"].min()
    latest["weeks_present"] = latest["keyword"].map(pres)
    latest["first_week"] = latest["keyword"].map(first)
    latest["product_cat"] = latest["cat_top"].isin(NV_PRODUCT_CATS)
    latest["early"] = latest["kw_type"].isin(["1주전에 없던", "1달전에 없던"]) | (
        (latest["kw_type"] == "1년전에 없던") & (latest["ath"] == "O"))
    latest["k_beauty_food"] = latest["cat_top"].isin(["화장품/미용", "식품"])
    # 비계절: 역대최고(ATH) 이거나 전년동기 대비 100% 이상 — 대하·한복·패딩 같은 연중 재등장 배제
    latest["non_seasonal"] = (latest["ath"] == "O") | (latest["yoy"].fillna(0) >= 100)
    r = latest[(latest["search_cnt"] >= NV_MIN_SEARCH) & latest["product_cat"] & latest["early"]
               & latest["non_seasonal"]].copy()
    r["score"] = (2 * (r["kw_type"] != "1년전에 없던") + 1 * (r["ath"] == "O") + 1 * r["k_beauty_food"]
                  + np.clip(r["mom"].fillna(0) / 50, 0, 3) + np.clip(r["yoy"].fillna(0) / 500, 0, 2)
                  + np.log10(r["search_cnt"]).round(1))
    return r.sort_values("score", ascending=False)


def seed_check(tt: pd.DataFrame, az_hist: pd.DataFrame, az_bq: pd.DataFrame) -> None:
    seeds = [s["keyword"] for s in json.loads((HERE / "seed_keywords.json").read_text())["seeds"]]
    print("\n=== 시드(확정 대박) 가 각 소스에 어떻게 보였나 (규칙 소급 검증) ===")
    print(f"  {'seed':<12} {'틱톡 top-100 (34주)':<38} {'아마존 top-100 (130주)':<42} 아마존 BQ 8천 유니버스 (13주)")
    for s in seeds:
        n = norm(s)
        t = tt[tt["hashtag"].map(norm) == n]
        a, b = az_hist[az_hist["n"] == n], az_bq[az_bq["n"].str.contains(n, regex=False)]
        tt_s = f"{t['cc'].unique().tolist()} {t['week'].min()}~{t['week'].max()}" if len(t) else "-"
        az_s = " | ".join(f"{r.cc} {r.az_status} {r.first_week}~{r.last_week} ({r.weeks_present}w)"
                          for r in a.itertuples()) or "-"
        bq_s = " | ".join(f"{r.cc} '{r.keyword}' {r.az_status} x{r.az_growth:.1f}" if r.az_growth == r.az_growth
                          else f"{r.cc} '{r.keyword}' {r.az_status}" for r in b.head(3).itertuples()) or "-"
        print(f"  {s:<12} {tt_s:<38} {az_s:<42} {bq_s}")


def main() -> None:
    d = HERE / "data"
    tt = pd.read_csv(d / "cand_tiktok.csv")
    am = pd.read_csv(d / "cand_amazon.csv")          # Firestore top-100, 긴 히스토리 (시드 검증)
    ab = pd.read_csv(d / "cand_amazon_bq.csv")       # BQ 원본, 넓은 유니버스 (현재 스크리닝)
    nv = pd.read_csv(d / "cand_naver.csv")
    az_hist, az = amazon_status(am), amazon_status_bq(ab)
    pd.set_option("display.width", 220)

    st = screen_tiktok(tt, az)
    st.to_csv(d / "screen_tiktok.csv", index=False)
    cols = ["cc", "hashtag", "category", "spike", "recent_views_wk", "weeks_present", "first_week",
            "az_status", "az_rising", "multi_cc", "score"]
    print(f"=== 틱톡 후보 (상품계열·비범용·tt점화, 상위 30 / 전체 {len(st)}) ===")
    print(st[st["product_cat"] & ~st["generic"] & st["tt_lit"]][cols].head(30).to_string(index=False))

    if (d / "cand_tiktok_raw.csv").exists():
        raw = pd.read_csv(d / "cand_tiktok_raw.csv")
        rel = pd.read_csv(d / "cand_related_tiktok.csv")
        sr = screen_tiktok_raw(raw, az, rel)
        sr.to_csv(d / "screen_tiktok_raw.csv", index=False)
        cols = ["hashtag", "spike", "recent_views_wk", "base_views_wk", "first_active", "is_new",
                "az_status", "src_az_us", "source_kw", "score"]
        lit = sr[sr["tt_lit"] & ~sr["generic"]]
        print(f"\n=== 틱톡 확장소스(raw_ {sr['hashtag'].nunique()}개) 후보: 점화 {len(lit)}개, 상위 40 ===")
        print(lit[cols].head(40).to_string(index=False))

    sn = screen_naver(nv)
    sn.to_csv(d / "screen_naver.csv", index=False)
    cols = ["keyword", "cat_top", "leaf", "kw_type", "search_cnt", "mom", "yoy", "ath", "weeks_present", "score"]
    print(f"\n=== 네이버 KR 조기신호 후보 (비계절, 상위 30 / 통과 {len(sn)}) ===")
    print(sn[cols].head(30).to_string(index=False))

    tt_norms = set(tt["hashtag"].map(norm)) - TT_GENERIC
    az["tt_match"] = az["n"].isin(tt_norms)
    az["product_cat"] = ~az["category"].isin(AZ_MEDIA_CATS)
    new = az[((az["az_status"] == "new") | az["rising"]) & az["product_cat"]
             & (az["max_search"] >= AZ_MIN_SEARCH)].sort_values(["tt_match", "az_growth"], ascending=False)
    new.to_csv(d / "screen_amazon_new.csv", index=False)
    cols = ["cc", "keyword", "category", "az_status", "az_growth", "max_search", "first_week", "weeks_present", "tt_match"]
    print(f"\n=== 아마존(BQ) 신규 진입·급상승 (상품 카테고리, 검색≥{AZ_MIN_SEARCH}, 상위 30 / 전체 {len(new)}, 틱톡 교차 {int(new['tt_match'].sum())}) ===")
    print(new[cols].head(30).to_string(index=False))

    seed_check(tt, az_hist, az)


if __name__ == "__main__":
    main()
