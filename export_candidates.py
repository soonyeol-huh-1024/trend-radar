"""
A→B 브리지 1단계: 한국에선 유행인데 해외(US/JP)는 조용한 상품(수출 후보) 즉시 판정.

입력: export_map.csv (ko_keyword, en_keyword '|' 변형, type, kr_signal, role)
해외 관측 소스 (즉시, 로컬 CSV):
  - 아마존 BQ US/JP 8천 키워드 유니버스 (부분일치, 최대 월검색·성장)
  - 아마존 Firestore top-100 130주 (부분일치, 잔류 주수)
  - 틱톡 raw 2,442 해시태그 (부분일치, 최근4주 조회) + 위클리 top-100
  - 우리 trend_daily 분석 이력 (hit_score)
판정: 해외유행 / 해외존재(소규모) / 해외조용(관측 부재)
  ※ '부재'는 관측 소스 한계(Helium10 추적집합·이웃 해시태그)라 약한 근거 →
     상위 후보는 워커 등록(구글·틱톡·아마존 직접 조회)으로 확정한다.

사용: python export_candidates.py
출력: data/export_candidates.csv
"""
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
norm = lambda s: re.sub(r"[^0-9a-z]", "", str(s).lower())


def main() -> None:
    d = HERE / "data"
    mp = pd.read_csv(HERE / "export_map.csv")
    ab = pd.read_csv(d / "cand_amazon_bq.csv")
    ab["kl"] = ab["keyword"].str.lower()
    am = pd.read_csv(d / "cand_amazon.csv")
    am["kl"] = am["keyword"].str.lower()
    raw = pd.read_csv(d / "cand_tiktok_raw.csv")
    raw["n"] = raw["hashtag"].map(norm)
    wks = sorted(raw["week_end"].unique())[-4:]
    hs = pd.read_csv(d / "hit_score_ALL.csv")

    rows = []
    for r in mp.itertuples():
        best = {"en_used": None, "az_us_kw": None, "az_us_search": 0, "az_us_growth": None, "az_jp_search": 0,
                "top100_weeks": 0, "tt_tags": 0, "tt_recent_M": 0.0, "tt_top_tag": None, "analyzed_hit": None}
        for en in [v.strip() for v in str(r.en_keyword).split("|") if v.strip()]:
            el, en_n = en.lower(), norm(en)
            cur = {"en_used": en}
            for cc in ("us", "jp"):
                s = ab[(ab["country"] == cc) & (ab["list"] == "search") & ab["kl"].str.contains(el, regex=False)]
                if len(s):
                    top = s.groupby("keyword")["avg_search"].max().sort_values(ascending=False)
                    k = top.index[0]
                    ser = s[s["keyword"] == k].sort_values("week")["avg_search"]
                    g = ser.iloc[-2:].mean() / max(ser.iloc[:2].mean(), 1) if len(ser) >= 4 else None
                    if cc == "us":
                        cur.update(az_us_kw=k, az_us_search=int(top.iloc[0]), az_us_growth=round(g, 1) if g else None)
                    else:
                        cur["az_jp_search"] = int(top.iloc[0])
            t100 = am[(am["cc"] == "us") & am["kl"].str.contains(el, regex=False)]
            cur["top100_weeks"] = int(t100["week"].nunique())
            tt = raw[raw["n"].str.contains(en_n, regex=False)] if en_n else raw.iloc[0:0]
            if len(tt):
                rec = tt[tt["week_end"].isin(wks)].groupby("hashtag")["views"].sum().sort_values(ascending=False)
                cur.update(tt_tags=int(tt["hashtag"].nunique()), tt_recent_M=round(rec.iloc[0] / 4e6, 2) if len(rec) else 0.0,
                           tt_top_tag=rec.index[0] if len(rec) else None)
            h = hs[hs["keyword"].str.lower() == el]
            if len(h):
                cur["analyzed_hit"] = f"{h['lang'].iloc[0]} hit{int(h['hit_pct'].max())}"
            score = cur.get("az_us_search", 0) + cur.get("tt_recent_M", 0) * 1e5 + cur["top100_weeks"] * 1e4
            if score > best.get("az_us_search", 0) + best.get("tt_recent_M", 0) * 1e5 + best["top100_weeks"] * 1e4 or best["en_used"] is None:
                best = {**best, **cur}
        hot = best["az_us_search"] >= 100_000 or best["tt_recent_M"] >= 10 or best["top100_weeks"] >= 8
        seen = best["az_us_search"] > 0 or best["az_jp_search"] > 0 or best["tt_tags"] > 0 or best["top100_weeks"] > 0
        best["overseas"] = "해외유행" if hot else ("해외존재(소규모)" if seen else "해외조용(관측부재)")
        rows.append({"ko": r.ko_keyword, "type": r.type, "role": r.role, "kr_signal": r.kr_signal, **best})

    res = pd.DataFrame(rows)
    res.to_csv(d / "export_candidates.csv", index=False)
    pd.set_option("display.width", 240)
    cols = ["role", "ko", "type", "en_used", "overseas", "az_us_search", "az_us_growth", "az_jp_search",
            "top100_weeks", "tt_tags", "tt_recent_M", "tt_top_tag", "analyzed_hit", "kr_signal"]
    order = {"해외조용(관측부재)": 0, "해외존재(소규모)": 1, "해외유행": 2}
    print(res.sort_values(["role", "overseas"], key=lambda s: s.map(order) if s.name == "overseas" else s)[cols]
          .to_string(index=False))


if __name__ == "__main__":
    main()
