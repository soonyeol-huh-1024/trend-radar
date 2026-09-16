"""
시드 키워드별 플랫폼 간 리드-래그(교차상관) 분석.

가설: 틱톡(발견) → 구글(탐색) → 아마존(구매) 순으로 시차가 존재한다.
lag k>0 는 "선행 플랫폼이 k주 앞선다" = corr(lead[t], follow[t+k]).

수준(levels)은 공통 추세 때문에 허위 상관이 생기기 쉬워
주간 변화량(diff)을 1차 근거로 삼고, 수준 결과는 참고용으로 함께 출력한다.

사용: python lead_lag.py [LANG] [MAX_LAG]   (기본 US, 12주)
출력: data/lead_lag_{LANG}.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
PAIRS = [("tt", "az"), ("tt", "gg"), ("gg", "az")]


def ccf(lead: np.ndarray, follow: np.ndarray, max_lag: int) -> dict[int, float]:
    """lag k: corr(lead[t], follow[t+k]). k<0 이면 follow가 앞선다."""
    out = {}
    n = len(lead)
    for k in range(-max_lag, max_lag + 1):
        if k >= 0:
            a, b = lead[: n - k], follow[k:]
        else:
            a, b = lead[-k:], follow[: n + k]
        if len(a) < 8 or a.std() == 0 or b.std() == 0:
            out[k] = np.nan
        else:
            out[k] = float(np.corrcoef(a, b)[0, 1])
    return out


def best_lag(c: dict[int, float]) -> tuple[int, float]:
    valid = {k: v for k, v in c.items() if not np.isnan(v)}
    if not valid:
        return 0, np.nan
    k = max(valid, key=valid.get)
    return k, valid[k]


def analyze_keyword(g: pd.DataFrame, max_lag: int) -> list[dict]:
    # 틱톡 데이터가 존재하는 구간(시차 측정의 시작점)으로 창을 제한
    tt_idx = g.index[g["tt"] > 0]
    if len(tt_idx) == 0:
        return []
    w = g.loc[tt_idx.min(): tt_idx.max()].copy()
    rows = []
    for lead, follow in PAIRS:
        lv = w[[lead, follow]].astype(float)
        dv = lv.diff().dropna()
        cl = ccf(lv[lead].values, lv[follow].values, max_lag)
        cd = ccf(dv[lead].values, dv[follow].values, max_lag)
        bl, bl_r = best_lag(cl)
        bd, bd_r = best_lag(cd)
        rows.append({
            "keyword": g["keyword"].iat[0], "lang": g["lang_code"].iat[0],
            "pair": f"{lead}->{follow}", "weeks": len(w),
            "diff_best_lag": bd, "diff_r": round(bd_r, 3),
            "diff_r_lag0": round(cd.get(0, np.nan), 3),
            "level_best_lag": bl, "level_r": round(bl_r, 3),
        })
    return rows


def summarize(res: pd.DataFrame) -> None:
    for pair, g in res.groupby("pair"):
        lags = g["diff_best_lag"]
        leads = int((lags > 0).sum())
        print(f"\n=== {pair}  (diff 기준, n={len(g)}) ===")
        print(f"  평균 시차 {lags.mean():+.2f}주 | 중앙값 {lags.median():+.1f}주 | "
              f"표준편차 {lags.std():.2f}")
        print(f"  선행(lag>0) {leads}/{len(g)} | 동시(0) {int((lags == 0).sum())} | "
              f"역행(lag<0) {int((lags < 0).sum())}")
        print(f"  best-lag 상관 평균 r={g['diff_r'].mean():.3f} | "
              f"lag0 상관 평균 r={g['diff_r_lag0'].mean():.3f}")


def main() -> None:
    lang = sys.argv[1].upper() if len(sys.argv) > 1 else "US"
    max_lag = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    df = pd.read_csv(HERE / "data" / f"series_{lang}.csv", parse_dates=["date"])
    df = df.sort_values(["keyword", "date"]).reset_index(drop=True)

    rows = []
    for _, g in df.groupby("keyword", sort=False):
        rows.extend(analyze_keyword(g.reset_index(drop=True), max_lag))
    res = pd.DataFrame(rows)
    path = HERE / "data" / f"lead_lag_{lang}.csv"
    res.to_csv(path, index=False)

    pd.set_option("display.width", 160)
    print(res.sort_values(["pair", "keyword"]).to_string(index=False))
    summarize(res)
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
