"""Seasonal Radar: 계절 배수 후보에 ItemScout 경쟁도(prdCnt)를 붙여 '자리가 빈' 키워드만 남긴다.

배수만 보면 '남성패딩'처럼 누구나 아는 대명사가 상위를 덮는다. 실제 가치는
검색 대비 등록 상품이 적은 키워드에 있으므로 monthly/prdCnt 비율로 재정렬한다.

입력: /tmp/seasonal_cand.csv (worker/_seasonal2.ts 산출)
출력: data/seasonal_radar.csv
"""
import csv, sys, time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from import_candidates import itemscout_cookie, ITEMSCOUT_URL

HDRS = {
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://itemscout.io", "referer": "https://itemscout.io/",
    "user-agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"),
}


def lookup(kw: str, cookie: str) -> dict:
    try:
        r = requests.post(ITEMSCOUT_URL, data={"keywords": kw}, timeout=20,
                          headers={**HDRS, "cookie": cookie})
        d = (r.json().get("data") or [{}])[0] if r.ok else {}
    except Exception:
        d = {}
    return {"monthly": (d.get("monthly") or {}).get("total"), "prd_cnt": d.get("prdCnt"),
            "cat": d.get("firstCategory")}


def main() -> None:
    cand = list(csv.DictReader(open("/tmp/seasonal_cand.csv")))
    cookie = itemscout_cookie()
    out = []
    for i, c in enumerate(cand, 1):
        m = lookup(c["keyword"], cookie)
        out.append({**c, **m})
        if i % 50 == 0:
            print(f"  {i}/{len(cand)}", flush=True)
        time.sleep(0.25)

    for r in out:
        mo, pc = r.get("monthly"), r.get("prd_cnt")
        # 수요/공급 비율 — 클수록 자리가 비어 있다
        r["ratio"] = round(mo / pc, 2) if mo and pc else None
    out.sort(key=lambda r: (r["ratio"] is None, -(r["ratio"] or 0)))

    cols = ["keyword", "yrs", "lift", "peakW", "monthly", "prd_cnt", "ratio", "cat"]
    with open("data/seasonal_radar.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"저장: data/seasonal_radar.csv ({len(out)}행)")


if __name__ == "__main__":
    main()
