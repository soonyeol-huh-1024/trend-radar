"""플랫폼을 건너뛰는 코너 — ③Cross-border(해외→국내) ⑤TikTok→Search(SNS→검색).

두 코너 모두 '저쪽에서 먼저 뜬 것이 이쪽에는 아직인가'를 본다.
한글 대응어는 자동 번역이 아니라 후보를 여러 개 두고 검색량이 가장 큰 것을 고른다
(하나만 보면 틀린다: '속눈썹클러스터' 0 vs '속눈썹연장세트' 40).
"""
from __future__ import annotations

from .common import cookie, enrich, itemscout, load_amazon, load_tiktok, weeks_of, write

# 해외 키워드 → 한글 후보. 자동 번역이 아니라 사람이 단어를 대는 자리.
# 후보를 3~4개 두고 검색량이 가장 큰 것을 고른다.
KO_CANDIDATES: dict[str, list[str]] = {
    "fall decor": ["가을소품", "가을인테리어", "가을장식", "가을데코"],
    "lash clusters": ["속눈썹클러스터", "속눈썹연장세트", "셀프속눈썹", "인조속눈썹"],
    "walking pad": ["워킹패드", "런닝머신", "트레드밀", "실내걷기운동기구"],
    "pimple patches": ["여드름패치", "트러블패치", "스팟패치"],
    "halloween decorations": ["할로윈장식", "할로윈소품", "할로윈파티용품"],
    "squishy": ["스퀴시", "말랑이", "스퀴시토이"],
    "hair claw clips": ["집게핀", "헤어집게핀", "대왕집게핀"],
    "cortisol": ["코르티솔", "코티솔영양제"],
    "shower steamer": ["샤워스티머", "입욕제", "샤워타블렛"],
    "sleep mask": ["수면안대", "실크안대", "온열안대"],
    "matcha": ["말차", "말차가루", "말차라떼"],
    "protein coffee": ["프로틴커피", "단백질커피"],
    "cloud slides": ["클라우드슬리퍼", "구름슬리퍼", "젤리슬리퍼"],
    "collagen gummies": ["콜라겐젤리", "콜라겐구미", "먹는콜라겐"],
    "castor oil": ["castor오일", "피마자유", "캐스터오일"],
}


def best_ko(cands: list[str], ck: str) -> dict:
    """후보 중 월 검색수가 가장 큰 것을 고른다."""
    got = [{"ko": k, **itemscout(k, ck)} for k in cands]
    got = [g for g in got if g.get("monthly")]
    return max(got, key=lambda g: g["monthly"]) if got else {"ko": cands[0], "monthly": 0, "prd_cnt": None}


def cross_border(top: int = 12) -> list[dict]:
    """해외에서 먼저 뜨고 한국에는 아직 덜 알려진 상품."""
    az = load_amazon()
    wk = weeks_of(az)[-1]
    # 최신 주차의 검색 상위 — 국가별로 모아 중복 키워드는 최대 검색량으로
    pool: dict[str, dict] = {}
    for r in az:
        if r["week"] != wk or r.get("list") != "search":
            continue
        kw = (r.get("keyword") or "").strip().lstrip("- ").lower()
        if not kw or len(kw) < 3:
            continue
        v = float(r.get("avg_search") or 0)
        if kw not in pool or v > pool[kw]["az_search"]:
            pool[kw] = {"az_kw": kw, "az_country": r["country"], "az_search": v,
                        "az_cat": r.get("category"), "week": wk}

    ck = cookie()
    out = []
    for en, cands in KO_CANDIDATES.items():
        ko = best_ko(cands, ck)
        az_hit = pool.get(en)
        out.append({
            "az_kw": en, "az_search": int(az_hit["az_search"]) if az_hit else None,
            "az_country": az_hit["az_country"] if az_hit else "us",
            "ko": ko["ko"], "monthly": ko.get("monthly"), "prd_cnt": ko.get("prd_cnt"),
            "gap": round((az_hit["az_search"] / ko["monthly"]), 1)
                   if az_hit and ko.get("monthly") else None,
        })
    # 격차가 큰 순 — 해외 대비 국내가 조용할수록 위로
    out.sort(key=lambda r: -(r["gap"] or 0))
    return out[:top]


# 해시태그 → 국내 검색어. 해시태그를 그대로 조회하면 대부분 0 이 나오므로
# 상품성 있는 태그만 골라 한글 대응어를 사람이 대준다.
TAG_KO: dict[str, list[str]] = {
    "squishy": ["스퀴시", "말랑이"], "Halloween": ["할로윈소품", "할로윈장식"],
    "OOTD": ["가을코디", "데일리룩"], "OutfitInspo": ["가을코디", "여성가을코디"],
    "Makeup": ["메이크업", "가을메이크업"], "GRWM": ["메이크업", "데일리메이크업"],
    "hair": ["헤어에센스", "헤어오일"], "HairTok": ["헤어에센스", "볼륨매직"],
    "ASMR": ["ASMR", "asmr마이크"], "Mukbang": ["먹방", "간편식"],
    "kitty": ["산리오", "헬로키티", "산리오굿즈"], "cortis": ["코르티스", "코르티스굿즈"],
    "nexz": ["넥스지"], "fall": ["가을소품", "가을인테리어"],
    "Tennis": ["테니스라켓", "테니스복"], "usopen": ["테니스라켓"],
    "CollegeFootball": ["미식축구공"], "NFL": ["미식축구유니폼"],
}
PRODUCT_CATS = ("shopping", "beauty", "food", "fashion", "sports", "health", "home")


def tiktok_to_search(top: int = 12) -> list[dict]:
    """SNS에서 검색으로 넘어오는 신호 — 해시태그가 뜬 뒤 국내 검색이 따라오는가."""
    tt = load_tiktok()
    wks = weeks_of(tt)
    cur, prev = wks[-1], wks[-5] if len(wks) >= 5 else wks[0]
    now = {r["hashtag"]: r for r in tt if r["week"] == cur and r["cc"] == "kr"}
    old = {r["hashtag"]: r for r in tt if r["week"] == prev and r["cc"] == "kr"}
    # 미국 태그도 함께 본다 — 국내로 넘어오기 전 단계를 잡기 위해
    for r in tt:
        if r["week"] == cur and r["cc"] == "us" and r["hashtag"] not in now:
            now[r["hashtag"]] = r
            o = [x for x in tt if x["week"] == prev and x["cc"] == "us" and x["hashtag"] == r["hashtag"]]
            if o:
                old[r["hashtag"]] = o[0]

    rows = []
    for tag, r in now.items():
        o = old.get(tag)
        if not o or not o["views_total"]:
            continue
        growth = r["views_total"] / o["views_total"] - 1
        cat = (r.get("category") or "").lower()
        # 상품성 있는 태그만 — K-pop·밈은 검색으로 넘어와도 팔 물건이 없다
        if growth < 0.02 or r["views_total"] < 5e7:
            continue
        if not any(c in cat for c in PRODUCT_CATS) and tag not in TAG_KO:
            continue
        rows.append({"hashtag": tag, "cc": r["cc"], "views_total": r["views_total"],
                     "growth4w": round(growth * 100, 1), "category": r.get("category")})
    rows.sort(key=lambda r: -r["growth4w"])

    ck = cookie()
    out = []
    for r in rows[:30]:
        cands = TAG_KO.get(r["hashtag"], [r["hashtag"]])
        ko = best_ko(cands, ck)
        r["ko"] = ko["ko"]
        r["monthly"] = ko.get("monthly")
        r["prd_cnt"] = ko.get("prd_cnt")
        r["ratio"] = round(ko["monthly"] / ko["prd_cnt"], 2) if ko.get("monthly") and ko.get("prd_cnt") else None
        if r["monthly"]:
            out.append(r)
    out.sort(key=lambda r: -(r["growth4w"] or 0))
    return out[:top]


if __name__ == "__main__":
    print("③ Cross-border")
    write("c03_crossborder.csv", cross_border(),
          ["az_kw", "az_country", "az_search", "ko", "monthly", "prd_cnt", "gap"])
    print("⑤ TikTok→Search")
    write("c05_tiktok_search.csv", tiktok_to_search(),
          ["hashtag", "cc", "views_total", "growth4w", "category", "ko", "monthly", "prd_cnt", "ratio"])
