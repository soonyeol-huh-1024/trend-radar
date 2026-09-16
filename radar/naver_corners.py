"""네이버 주간 키워드 기반 코너 — ①This Week 10 ②Emerging ⑥Search→Commerce ⑦Falling.

네 코너 모두 같은 소스(cand_naver.csv, 29주 × 19,793키워드)를 보되 보는 구간이 다르다.
 ① 이번 주 절대 규모 + 상승   ② 아직 작지만 막 오르기 시작  ⑥ 검색이 상품 관심으로  ⑦ 피크 이후 하락
"""
from __future__ import annotations

from statistics import mean

from .common import enrich, load_naver, series, weeks_of, write

MIN_MONTHLY = 3_000       # 이보다 작으면 시장이라 부르기 어렵다
GENERIC_PRD = 100_000     # 등록 상품이 이만큼이면 대명사로 본다


def _tail(rows: list[dict], kw: str, n: int) -> list[float]:
    return [v for _, v in series(rows, kw)][-n:]


def this_week_10(rows: list[dict], top: int = 14) -> list[dict]:
    """이번 주 가장 주목할 키워드 — 규모와 상승을 함께 본다."""
    wk = weeks_of(rows)[-1]
    cur = [r for r in rows if r["week"] == wk and r["search_cnt"] and r["search_cnt"] >= 10_000]
    for r in cur:
        s = _tail(rows, r["keyword"], 5)
        prev = mean(s[:-1]) if len(s) > 1 else None
        r["wow"] = round((s[-1] / prev - 1) * 100, 1) if prev else None
        # 규모(log)와 상승률을 곱해 '크면서 오른 것'을 위로
        r["score"] = round((r["search_cnt"] ** 0.5) * max(r["wow"] or 0, 0) ** 0.5, 1)
    cur = [r for r in cur if (r["wow"] or 0) > 20]
    cur.sort(key=lambda r: -r["score"])
    got = enrich(cur[:top * 4])
    # 워터파크·영화관 같은 경험재와 등록 상품 과포화 대명사는 뺀다
    got = [g for g in got if not g["is_experience"] and (g.get("prd_cnt") or 0) < GENERIC_PRD]
    return got[:top]


def emerging(rows: list[dict], top: int = 14) -> list[dict]:
    """이제 막 상승하기 시작한 키워드 — 앞 구간은 조용하다 최근 4주에 꺾여 올라온 것."""
    wk = weeks_of(rows)[-1]
    out = []
    for r in [x for x in rows if x["week"] == wk and x["search_cnt"]]:
        s = _tail(rows, r["keyword"], 12)
        if len(s) < 10:
            continue
        base, recent = mean(s[:-4]), mean(s[-4:])
        if base <= 0 or recent < 3_000:
            continue
        lift = recent / base
        # 이미 크게 뜬 것이 아니라 '막 시작'한 구간: 완만한 기울기 + 직전까지 조용
        if not (1.6 <= lift <= 8) or max(s[:-4]) > recent:
            continue
        r["base"] = int(base)
        r["recent"] = int(recent)
        r["lift"] = round(lift, 2)
        out.append(r)
    out.sort(key=lambda r: -r["lift"])
    return enrich(out[:top])


def search_to_commerce(rows: list[dict], top: int = 14) -> list[dict]:
    """검색 상승이 상품 관심으로 이어지는 키워드 — 오르는데 파는 사람은 아직 적다."""
    wk = weeks_of(rows)[-1]
    cur = [r for r in rows if r["week"] == wk and r["search_cnt"] and r["search_cnt"] >= MIN_MONTHLY]
    for r in cur:
        s = _tail(rows, r["keyword"], 8)
        r["lift8"] = round(s[-1] / mean(s[:4]), 2) if len(s) >= 8 and mean(s[:4]) else None
    cur = [r for r in cur if (r["lift8"] or 0) >= 1.3]
    cur.sort(key=lambda r: -(r["lift8"] or 0))
    got = enrich(cur[:80])
    # 자리가 빈 순서로 재정렬 — 경험/티켓류는 prdCnt 가 낮아도 상품 근거가 아니므로 제외
    got = [g for g in got if g.get("ratio") and not g["is_experience"]
           and (g.get("prd_cnt") or 0) < GENERIC_PRD]
    got.sort(key=lambda g: -g["ratio"])
    return got[:top]


def falling(rows: list[dict], top: int = 12) -> list[dict]:
    """이미 정점을 지나 하락하는 트렌드 — 피크가 최근 6개월 안이고 지금은 절반 이하."""
    wk = weeks_of(rows)[-1]
    out = []
    for r in [x for x in rows if x["week"] == wk and x["search_cnt"]]:
        s = _tail(rows, r["keyword"], 29)
        if len(s) < 16:
            continue
        peak = max(s)
        pi = s.index(peak)
        if peak < 30_000 or pi > len(s) - 5 or pi < 2:
            continue                       # 피크가 너무 최근이면 아직 하락 판단 불가
        drop = s[-1] / peak
        if drop > 0.5:
            continue
        r["peak"] = int(peak)
        r["weeks_since_peak"] = len(s) - 1 - pi
        r["vs_peak"] = round(drop * 100, 1)
        out.append(r)
    out.sort(key=lambda r: (r["vs_peak"], -r["peak"]))
    return enrich(out[:top])


COLS = ["keyword", "cat_top", "search_cnt", "monthly", "prd_cnt", "ratio", "nv_cat", "image"]

if __name__ == "__main__":
    rows = load_naver()
    print(f"네이버 주간 키워드 {len(rows):,}행 / 최신 {weeks_of(rows)[-1]}")
    print("① This Week 10");        write("c01_this_week.csv", this_week_10(rows), COLS + ["wow", "score"])
    print("② Emerging");            write("c02_emerging.csv", emerging(rows), COLS + ["base", "recent", "lift"])
    print("⑥ Search→Commerce");     write("c06_search_commerce.csv", search_to_commerce(rows), COLS + ["lift8"])
    print("⑦ Falling Trends");      write("c07_falling.csv", falling(rows), COLS + ["peak", "vs_peak", "weeks_since_peak"])
