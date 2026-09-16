"""④ Seasonal Radar — 3년+ 주간 시계열에서 2~8주 뒤 오를 계절 키워드.

소스: Firestore itemscout-data-358206/trenddata/naver_keyword_trend (7,544개, 최대 471주).
배수만 보면 '남성패딩'(등록 상품 388만)처럼 누구나 아는 대명사가 덮으므로
common.enrich 로 경쟁도를 붙여 '자리가 빈' 것만 남긴다.
"""
from __future__ import annotations

import datetime as dt
from urllib.parse import unquote

from google.cloud import firestore

from .common import enrich, write

PROJECT, DATABASE = "itemscout-data-358206", "trenddata"
MIN_WEEKS = 156          # 3년 미만은 계절 판단 불가
MIN_MONTHLY = 3_000
GENERIC_PRD = 100_000    # 등록 상품이 이만큼이면 대명사


def _wk(d: dt.date) -> int:
    return ((d - dt.date(d.year, 1, 1)).days // 7) % 52


def candidates(today: dt.date | None = None, min_lift: float = 2.0) -> list[dict]:
    today = today or dt.date.today()
    db = firestore.Client(project=PROJECT, database=DATABASE)
    now_w = _wk(today)
    out = []
    for doc in db.collection("naver_keyword_trend").stream():
        v = doc.to_dict() or {}
        arr = [float(x.get("ratio") or 0) for x in (v.get("data") or [])]
        if len(arr) < MIN_WEEKS:
            continue
        upd = v.get("updated_at")
        upd = upd.date() if hasattr(upd, "date") else today
        last_w, yrs = _wk(upd), min(len(arr) // 52, 5)

        def at(w: int) -> float | None:
            back = (last_w - w) % 52
            vals = [arr[len(arr) - 1 - back - y * 52] for y in range(yrs)
                    if len(arr) - 1 - back - y * 52 >= 0]
            return sum(vals) / len(vals) if len(vals) >= 2 else None

        cur = at(now_w)
        if not cur or cur < 2:
            continue
        peak, peak_w = 0.0, 0
        for k in range(2, 9):
            p = at((now_w + k) % 52)
            if p and p > peak:
                peak, peak_w = p, k
        # 직전 8주가 이미 더 높았으면 계절이 지난 것 (여름 상품 오탐)
        summer = max((at((now_w - k) % 52) or 0) for k in range(1, 9))
        if summer > peak or peak / cur < min_lift:
            continue
        out.append({"keyword": unquote(doc.id), "yrs": yrs, "weeks": len(arr),
                    "lift": round(peak / cur, 2), "peak_week": peak_w})
    out.sort(key=lambda r: -r["lift"])
    return out


def radar(today: dt.date | None = None, top: int = 16) -> tuple[list[dict], list[dict]]:
    """(상품 후보, 나들이·체험 후보) 두 갈래로 나눠 돌려준다.

    티켓·입장권류는 prdCnt 가 낮은 게 '자리가 비어서'가 아니라 애초에 네이버쇼핑에서
    파는 물건이 아니기 때문이다. 같은 표에 섞으면 셀러를 헛걸음시킨다.
    """
    got = enrich(candidates(today))
    got = [g for g in got if (g.get("monthly") or 0) >= MIN_MONTHLY and g.get("ratio")]
    exp = [g for g in got if g["is_experience"] or (g.get("prd_cnt") or 0) < 30]
    prod = [g for g in got if g not in exp and (g.get("prd_cnt") or 0) < GENERIC_PRD]
    exp.sort(key=lambda g: -(g.get("monthly") or 0))
    prod.sort(key=lambda g: -g["ratio"])
    return prod[:top], exp[:top]


COLS = ["keyword", "yrs", "lift", "peak_week", "monthly", "prd_cnt", "ratio", "nv_cat", "image"]

if __name__ == "__main__":
    print("④ Seasonal Radar")
    prod, exp = radar()
    write("c04_seasonal_product.csv", prod, COLS)
    write("c04_seasonal_outing.csv", exp, COLS)
