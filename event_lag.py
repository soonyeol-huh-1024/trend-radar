"""
이벤트 기반 리드-래그: "틱톡 피크 → 아마존/구글 피크까지 몇 주" 를 직접 측정.

CCF(lead_lag.py)는 정상 공변동을 재지만, 트렌드 전이는 이산적 스파이크 이벤트라
피크 간격·급등 시작점(breakout) 간격이 사업 가설에 더 충실한 조작화다.

- peak_lag     : az/gg 피크 주차 − tt 피크 주차 (양수 = 틱톡이 먼저)
- breakout_lag : 각 플랫폼이 창 내 최댓값의 BO_RATIO 를 처음 넘은 주차의 차이
- tt_peak_pos  : 틱톡 피크가 창 초입(start)이면 실제 바이럴이 데이터 이전일 의심,
                 말미(end)면 아직 상승 중이라 아마존 반응이 미도착일 수 있음.

사용: python event_lag.py [LANG]   (기본 US)
출력: data/event_lag_{LANG}.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
BO_RATIO = 0.5   # 급등 시작점 = 창 내 최댓값의 50% 최초 돌파
EDGE = 4         # 창 양끝 4주 이내 피크는 경계 의심


def breakout_idx(s: np.ndarray) -> int:
    thr = s.max() * BO_RATIO
    return int(np.argmax(s >= thr)) if s.max() > 0 else -1


def analyze(g: pd.DataFrame) -> dict | None:
    tt_idx = g.index[g["tt"] > 0]
    if len(tt_idx) == 0:
        return None
    w = g.loc[tt_idx.min(): tt_idx.max()].reset_index(drop=True)
    n = len(w)
    tt, az, gg = (w[c].astype(float).values for c in ("tt", "az", "gg"))
    tp, ap, gp = int(tt.argmax()), int(az.argmax()), int(gg.argmax())
    tb, ab, gb = breakout_idx(tt), breakout_idx(az), breakout_idx(gg)
    pos = "start" if tp < EDGE else ("end" if tp >= n - EDGE else "mid")
    d = lambda i: w["date"].iat[i].date().isoformat()
    return {
        "keyword": g["keyword"].iat[0], "weeks": n, "tt_peak_pos": pos,
        "tt_peak": d(tp), "az_peak": d(ap), "gg_peak": d(gp),
        "az_peak_lag": ap - tp, "gg_peak_lag": gp - tp,
        "tt_bo": d(tb), "az_bo": d(ab), "gg_bo": d(gb),
        "az_bo_lag": ab - tb, "gg_bo_lag": gb - tb,
        "tt_peak_val": round(tt.max(), 1), "az_peak_val": round(az.max(), 1),
    }


def summarize(res: pd.DataFrame, label: str, col: str) -> None:
    s = res[col]
    print(f"  {label:<14} 평균 {s.mean():+.1f}주 | 중앙값 {s.median():+.1f}주 | "
          f"표준편차 {s.std():.1f} | 틱톡선행 {(s > 0).sum()}/{len(s)} | "
          f"동시 {(s == 0).sum()} | 역행 {(s < 0).sum()}")


def main() -> None:
    lang = sys.argv[1].upper() if len(sys.argv) > 1 else "US"
    df = pd.read_csv(HERE / "data" / f"series_{lang}.csv", parse_dates=["date"])
    df = df.sort_values(["keyword", "date"]).reset_index(drop=True)
    rows = [r for _, g in df.groupby("keyword", sort=False)
            if (r := analyze(g.reset_index(drop=True)))]
    res = pd.DataFrame(rows)
    path = HERE / "data" / f"event_lag_{lang}.csv"
    res.to_csv(path, index=False)

    pd.set_option("display.width", 200)
    print(res.to_string(index=False))

    print(f"\n=== 전체 (n={len(res)}) ===")
    summarize(res, "tt→az 피크", "az_peak_lag")
    summarize(res, "tt→gg 피크", "gg_peak_lag")
    summarize(res, "tt→az 급등시작", "az_bo_lag")
    summarize(res, "tt→gg 급등시작", "gg_bo_lag")

    mid = res[res["tt_peak_pos"] == "mid"]
    print(f"\n=== 틱톡 피크가 창 중간(경계 의심 제외) 만 (n={len(mid)}) ===")
    if len(mid):
        summarize(mid, "tt→az 피크", "az_peak_lag")
        summarize(mid, "tt→az 급등시작", "az_bo_lag")
    print(f"\n경계 의심(start/end): "
          f"{res[res['tt_peak_pos'] != 'mid'][['keyword', 'tt_peak_pos', 'tt_peak']].to_dict('records')}")
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
