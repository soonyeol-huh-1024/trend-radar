"""
"대박" 키워드 식별: tt→gg→az 체인이 완성돼 아마존 수요가 실제로 뛴 키워드.

조작적 정의 v2 (피크 기반 — v1 'late vs early' 는 창 중간에 터지고 식은
labubu 같은 대박을 놓쳐 폐기):
  - 창 = 틱톡 데이터 구간(2024-08~). 창 앞 52주 평균 = 사전 베이스라인(pre).
  - az_peak4  = 창 내 4주 이동평균 최고점 (단주 잡음 배제)
  - az_surge  = az_peak4 / max(az_pre, 1)   (틱톡 이전 대비 몇 배 터졌나)
  - az_surge_abs = az_peak4 − az_pre          (절대 상승폭)
  - sustain   = az_late(마지막 26주 평균) / az_peak4   (식었나, 유지되나 — 특성)
  - az_ath    = 창 안에 아마존 역대 최고점이 있는가
  - chain     = 틱톡 스파이크 ≥1 AND gg_surge ≥ 2 AND az_surge ≥ 2 AND az_peak4 ≥ 10
  2026 레벨 인플레이션 때문에 절대 배율보다 풀 내 백분위(pct)로 본다.
  주의: 베이스라인이 0에 가까운 '신규' 키워드에 유리한 정의 — 목표(아직 안 뜬
  신규 키워드 발굴)와 부합하지만, 기성 브랜드의 재부상은 상대적으로 낮게 잡힌다.

사용: python hit_score.py [LANG|ALL]   (기본 ALL, KR 제외)
출력: data/hit_score_{LANG}.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd

from spike_events import onsets

HERE = Path(__file__).parent
PRE_W, EDGE_W = 52, 26


def score(g: pd.DataFrame) -> dict | None:
    tt_idx = g.index[g["tt"] > 0]
    if len(tt_idx) < 40:
        return None
    s, e = tt_idx.min(), tt_idx.max()
    w = g.loc[s:e]
    pre = g.loc[max(0, s - PRE_W): s - 1]
    late = w.iloc[-EDGE_W:]
    az_pre = float(pre["az"].mean()) if len(pre) else 0.0
    gg_pre = float(pre["gg"].mean()) if len(pre) else 0.0
    az_pk = float(w["az"].rolling(4, min_periods=2).mean().max())
    gg_pk = float(w["gg"].rolling(4, min_periods=2).mean().max())
    az_l = float(late["az"].mean())
    n_tt = len(onsets(w["tt"].astype(float).reset_index(drop=True)))
    az_surge, gg_surge = az_pk / max(az_pre, 1.0), gg_pk / max(gg_pre, 1.0)
    return {
        "keyword": g["keyword"].iat[0], "lang": g["lang_code"].iat[0],
        "az_pre": round(az_pre, 1), "az_peak4": round(az_pk, 1), "az_late": round(az_l, 1),
        "az_surge": round(az_surge, 2), "az_surge_abs": round(az_pk - az_pre, 1),
        "sustain": round(az_l / max(az_pk, 1.0), 2),
        "az_ath": bool(w["az"].max() >= 0.95 * g["az"].max()),
        "gg_surge": round(gg_surge, 2), "tt_max": round(float(w["tt"].max()), 1),
        "n_tt_spk": n_tt,
        "chain": bool(n_tt >= 1 and gg_surge >= 2 and az_surge >= 2 and az_pk >= 10),
    }


def main() -> None:
    lang = sys.argv[1].upper() if len(sys.argv) > 1 else "ALL"
    df = pd.read_csv(HERE / "data" / f"series_{lang}.csv", parse_dates=["date"])
    df = df[df["lang_code"] != "KR"].sort_values(["keyword", "lang_code", "date"])
    seeds = {s["keyword"] for s in json.loads((HERE / "seed_keywords.json").read_text())["seeds"]}

    rows = [r for _, g in df.groupby(["keyword", "lang_code"], sort=False)
            if (r := score(g.reset_index(drop=True)))]
    res = pd.DataFrame(rows)
    for c in ("az_surge", "az_surge_abs", "gg_surge", "tt_max"):
        res[f"{c}_pct"] = (res[c].rank(pct=True) * 100).round(0).astype(int)
    res["hit_pct"] = ((res["az_surge_pct"] + res["az_surge_abs_pct"] + res["gg_surge_pct"]) / 3).round(0).astype(int)
    res["seed"] = res["keyword"].isin(seeds).map({True: "★", False: ""})
    res = res.sort_values("hit_pct", ascending=False).reset_index(drop=True)
    path = HERE / "data" / f"hit_score_{lang}.csv"
    res.to_csv(path, index=False)

    pd.set_option("display.width", 220)
    cols = ["seed", "keyword", "lang", "hit_pct", "az_pre", "az_peak4", "az_late",
            "az_surge", "az_surge_abs", "sustain", "az_ath", "gg_surge", "tt_max", "n_tt_spk", "chain"]
    print(f"조합 {len(res)}개 (KR 제외) | chain 완성 {int(res['chain'].sum())}개 | "
          f"az_ath 창 내 {int(res['az_ath'].sum())}개\n")
    print("=== hit_pct 상위 30 ===")
    print(res[cols].head(30).to_string(index=False))
    print("\n=== 시드 위치 (정의 교정용) ===")
    print(res[res["seed"] == "★"][cols].to_string(index=False))
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
