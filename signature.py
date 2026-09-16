"""
대박 vs 비대박 키워드의 공통점(시그니처) 추출.

hit_score(자동 특성) + keyword_attrs(의미 주석)를 결합해 키워드 단위로
라벨링하고, 특성값별 대박률을 비교한다.

라벨 (키워드 단위, 국가 중 최고 조합 기준):
  hit    = max hit_pct ≥ HIT_PCT AND chain 완성 조합 존재
  nonhit = max hit_pct < NONHIT_PCT
  mid    = 그 사이 (비율 계산에서 제외)

사용: python signature.py
출력: data/signature_keywords.csv
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
HIT_PCT, NONHIT_PCT = 80, 60
ATTRS = ["type", "category", "origin", "consumable", "price", "novelty"]


def load_attrs() -> pd.DataFrame:
    a = pd.read_csv(HERE / "keyword_attrs.csv", dtype=str).fillna("")
    base = a[a["alias_of"] == ""].set_index("keyword")
    for i, r in a[a["alias_of"] != ""].iterrows():          # 별칭은 원본 속성 복사
        if r["type"] == "" and r["alias_of"] in base.index:
            a.loc[i, ATTRS] = base.loc[r["alias_of"], ATTRS].values
    a["canon"] = a.apply(lambda r: r["alias_of"] or r["keyword"], axis=1)
    return a


def keyword_level(hs: pd.DataFrame) -> pd.DataFrame:
    g = hs.groupby("keyword")
    kw = pd.DataFrame({
        "max_hit_pct": g["hit_pct"].max(),
        "any_chain": g["chain"].any(),
        "n_hit_ctry": g.apply(lambda d: int(((d["hit_pct"] >= HIT_PCT) & d["chain"]).sum())),
        "n_ctry": g.size(),
        "min_az_pre": g["az_pre"].min(),
        "max_gg_surge": g["gg_surge"].max(),
        "sustain_at_best": g.apply(lambda d: d.loc[d["hit_pct"].idxmax(), "sustain"]),
    })
    kw["label"] = "mid"
    kw.loc[(kw["max_hit_pct"] >= HIT_PCT) & kw["any_chain"], "label"] = "hit"
    kw.loc[kw["max_hit_pct"] < NONHIT_PCT, "label"] = "nonhit"
    return kw.reset_index()


def rate_table(df: pd.DataFrame, col: str) -> pd.DataFrame:
    d = df[df["label"] != "mid"]
    t = d.groupby(col)["label"].agg(n="size", hits=lambda s: int((s == "hit").sum()))
    t["hit_rate"] = (t["hits"] / t["n"] * 100).round(0).astype(int)
    return t[t["n"] >= 3].sort_values(["hit_rate", "n"], ascending=False)


def main() -> None:
    hs = pd.read_csv(HERE / "data" / "hit_score_ALL.csv")
    attrs = load_attrs()
    hs = hs.merge(attrs[["keyword", "canon"]], on="keyword", how="left")
    hs["keyword"] = hs["canon"].fillna(hs["keyword"])   # 별칭(일본어 표기)을 원본으로 합침
    kw = keyword_level(hs).merge(
        attrs[attrs["alias_of"] == ""][["keyword"] + ATTRS], on="keyword", how="left")
    kw[ATTRS] = kw[ATTRS].fillna("?")
    kw.to_csv(HERE / "data" / "signature_keywords.csv", index=False)

    pd.set_option("display.width", 200)
    print(f"키워드 {len(kw)}개: hit {int((kw.label=='hit').sum())} / "
          f"nonhit {int((kw.label=='nonhit').sum())} / mid {int((kw.label=='mid').sum())} "
          f"(hit≥{HIT_PCT}+chain, nonhit<{NONHIT_PCT})\n")

    print("=== 대박 키워드 목록 ===")
    cols = ["keyword", "max_hit_pct", "n_hit_ctry", "n_ctry", "min_az_pre",
            "max_gg_surge", "sustain_at_best"] + ATTRS
    print(kw[kw.label == "hit"].sort_values("max_hit_pct", ascending=False)[cols].to_string(index=False))

    for c in ATTRS:
        print(f"\n=== {c} 별 대박률 (n≥3) ===")
        print(rate_table(kw, c).to_string())

    kw["az_pre_bucket"] = pd.cut(kw["min_az_pre"], [-1, 2, 10, 25, 1000],
                                 labels=["<2 (신규)", "2-10", "10-25", ">25 (기성)"])
    print("\n=== 틱톡 이전 아마존 베이스라인(az_pre) 구간별 대박률 ===")
    print(rate_table(kw, "az_pre_bucket").to_string())

    d = kw[kw.label != "mid"]
    print("\n=== 수치 특성 중앙값: hit vs nonhit ===")
    print(d.groupby("label")[["min_az_pre", "max_gg_surge", "sustain_at_best", "n_ctry"]]
          .median().round(2).to_string())


if __name__ == "__main__":
    main()
