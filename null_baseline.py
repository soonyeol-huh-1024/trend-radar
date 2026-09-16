"""
spike_events 반응률의 우연 대조군.

az/gg 스파이크가 촘촘하면 틱톡 onset 창(-BACK~+FWD) 안에 우연히 걸릴 확률이
원래 높다. 실제 az/gg onset 은 고정한 채 틱톡 onset 만 무작위로 뽑아
'우연 반응률' 분포를 만들고 실제 반응률과 비교한다.

사용: python null_baseline.py [LANG] [N_ITER]   (기본 US, 1000)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from spike_events import BASE_W, match, onsets

HERE = Path(__file__).parent


def main() -> None:
    lang = sys.argv[1].upper() if len(sys.argv) > 1 else "US"
    n_iter = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    rng = np.random.default_rng(42)
    df = pd.read_csv(HERE / "data" / f"series_{lang}.csv", parse_dates=["date"])
    df = df.sort_values(["keyword", "date"]).reset_index(drop=True)

    real = {"az": [], "gg": []}
    null = {"az": [], "gg": []}
    for _, g in df.groupby("keyword", sort=False):
        g = g.reset_index(drop=True)
        tt_idx = g.index[g["tt"] > 0]
        if len(tt_idx) == 0:
            continue
        w = g.loc[tt_idx.min(): tt_idx.max()].reset_index(drop=True)
        ev = {c: onsets(w[c].astype(float)) for c in ("tt", "az", "gg")}
        k, n = len(ev["tt"]), len(w)
        if k == 0:
            continue
        for c in ("az", "gg"):
            real[c] += [match(t, ev[c]) is not None for t in ev["tt"]]
            for _ in range(n_iter):
                fake = rng.integers(BASE_W, n, size=k)
                null[c] += [match(int(t), ev[c]) is not None for t in fake]

    for c in ("az", "gg"):
        r, z = np.mean(real[c]), np.mean(null[c])
        print(f"tt→{c}: 실제 반응률 {r:.0%} | 우연 반응률 {z:.0%} | "
              f"차이 {r - z:+.0%} (실제 이벤트 {len(real[c])}건, 대조 {len(null[c]):,}건)")


if __name__ == "__main__":
    main()
