"""
국소 스파이크 이벤트 스터디: 레벨 드리프트에 면역인 리드-래그 측정.

배경: 저장된 gg/az 합성 시계열은 분석 시점 연관어 선정 편향으로 최근 구간이
구조적으로 높다(2026 평균 az +30%, gg +50%). 전역 최댓값 기반 피크는 이 드리프트에
끌려가므로, "직전 BASE_W주 이동중앙값 대비 배율"로 국소 스파이크를 잡는다.

- 스파이크 주차: value / baseline >= RATIO 이고 value >= MIN_ABS
- 이벤트 onset: 연속 스파이크 구간의 첫 주 (피크가 아닌 '상승 시작')
- 틱톡 onset 마다 [-BACK, +FWD] 창 안에서 |시차| 최소인 az/gg onset 을 매칭.
  양수 시차 = 틱톡이 먼저. 창 안에 없으면 '무반응'.

사용: python spike_events.py [LANG]   (기본 US)
출력: data/spike_events_{LANG}.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
BASE_W = 13      # 기준선: 직전 13주(≈분기) 이동중앙값
RATIO = 1.8      # 기준선 대비 1.8배 이상이면 스파이크
MIN_ABS = 8.0    # 0-100 스케일에서 절대값 하한 (저레벨 잡음 배제)
BACK, FWD = 8, 16   # 틱톡 onset 기준 매칭 창(주)


def onsets(s: pd.Series) -> list[int]:
    """연속 스파이크 구간의 첫 주 인덱스 목록."""
    base = s.shift(1).rolling(BASE_W, min_periods=BASE_W).median().clip(lower=1.0)
    spike = (s / base >= RATIO) & (s >= MIN_ABS)
    starts = spike & ~spike.shift(1, fill_value=False)
    return [int(i) for i in np.flatnonzero(starts.values)]


def match(t_on: int, cand: list[int]) -> int | None:
    inwin = [c for c in cand if -BACK <= c - t_on <= FWD]
    return min(inwin, key=lambda c: abs(c - t_on)) - t_on if inwin else None


def analyze(g: pd.DataFrame) -> list[dict]:
    tt_idx = g.index[g["tt"] > 0]
    if len(tt_idx) == 0:
        return []
    w = g.loc[tt_idx.min(): tt_idx.max()].reset_index(drop=True)
    ev = {c: onsets(w[c].astype(float)) for c in ("tt", "az", "gg")}
    rows = []
    for t in ev["tt"]:
        rows.append({
            "keyword": g["keyword"].iat[0],
            "tt_onset": w["date"].iat[t].date().isoformat(),
            "tt_val": round(float(w["tt"].iat[t]), 1),
            "az_lag": match(t, ev["az"]), "gg_lag": match(t, ev["gg"]),
            "n_tt_ev": len(ev["tt"]), "n_az_ev": len(ev["az"]), "n_gg_ev": len(ev["gg"]),
        })
    return rows


def summarize(res: pd.DataFrame, col: str, label: str) -> None:
    lag = res[col].dropna()
    n = len(res)
    if n == 0:
        print(f"  {label}: 틱톡 이벤트 없음")
        return
    print(f"  {label:<6} 틱톡 이벤트 {n}건 → 반응 {len(lag)}건 ({len(lag)/n:.0%})")
    if len(lag):
        print(f"         시차 평균 {lag.mean():+.1f}주 | 중앙값 {lag.median():+.1f}주 | "
              f"표준편차 {lag.std():.1f} | 틱톡선행 {(lag > 0).sum()} | "
              f"동시 {(lag == 0).sum()} | 역행 {(lag < 0).sum()}")


def main() -> None:
    lang = sys.argv[1].upper() if len(sys.argv) > 1 else "US"
    df = pd.read_csv(HERE / "data" / f"series_{lang}.csv", parse_dates=["date"])
    df = df.sort_values(["keyword", "date"]).reset_index(drop=True)
    rows = []
    for _, g in df.groupby("keyword", sort=False):
        rows.extend(analyze(g.reset_index(drop=True)))
    res = pd.DataFrame(rows)
    path = HERE / "data" / f"spike_events_{lang}.csv"
    res.to_csv(path, index=False)

    pd.set_option("display.width", 200)
    print(f"파라미터: 기준선 {BASE_W}주 중앙값 × {RATIO}, 절대값≥{MIN_ABS}, 창 -{BACK}~+{FWD}주\n")
    print(res.to_string(index=False) if len(res) else "(틱톡 스파이크 이벤트 없음)")
    print(f"\n=== 전체 ({res['keyword'].nunique() if len(res) else 0}개 키워드) ===")
    summarize(res, "az_lag", "tt→az")
    summarize(res, "gg_lag", "tt→gg")
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
