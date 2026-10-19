"""셀러KIM 8호 숫자 고정: 아이템스카우트(월 검색·상품 수·대표 이미지) + 계절 곡선(naver_keyword_trend 9년).
한 호에서 쓰는 숫자는 모두 이 파일(issue08_data.json)에서 가져온다 (GUIDE '한 키워드에는 한 숫자만').
"""
import datetime as dt, json, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from google.cloud import firestore
sys.path.insert(0, str(Path(__file__).parent.parent))
from radar.common import enrich

OUT = Path(__file__).parent / "issue08_data.json"
TODAY = dt.date(2026, 10, 19)
IS_KW = ["메디큐브", "메디큐브패드", "메디큐브제로모공패드", "메디큐브부스터프로", "361도", "361도러닝화", "먼작귀", "치이카와",
         "치이카와팝콘통", "치이카와인어섬", "치이카와굿즈", "어그", "어그뮬", "공덕키링", "유니클로", "무신사", "스파오", "탑텐", "h&m",
         "크리스마스트리", "절임배추", "내장산단풍", "스키복", "다이어리", "방한화", "졸업식꽃다발", "아이스조끼", "넥쿨러", "냉감패드",
         "캐리비안베이", "아이폰18", "갤럭시폴드8", "송편", "어드벤트캘린더", "보온물주머니", "제습기", "닌자에어프라이어", "레고"]
SEASON_KW = ["크리스마스트리", "절임배추", "내장산단풍", "스키복", "다이어리", "방한화", "졸업식꽃다발", "아이스조끼", "넥쿨러", "냉감패드"]


def season(db, kw):
    d = db.collection("naver_keyword_trend").document(quote(kw, safe="")).get()
    if not d.exists:
        return None
    v = d.to_dict(); arr = np.array([float(x.get("ratio") or 0) for x in v["data"]])
    upd = v["updated_at"].date(); last = upd - dt.timedelta(days=upd.weekday() + 7)
    dates = [last - dt.timedelta(weeks=len(arr) - 1 - i) for i in range(len(arr))]
    wk = np.zeros(53); wc = np.zeros(53); mon = np.zeros(12); mc = np.zeros(12); yrs = 0
    for y in range(last.year - 5, last.year):
        idx = [i for i, x in enumerate(dates) if x.year == y]
        if len(idx) < 48 or arr[idx].max() <= 0:
            continue
        yrs += 1; x = arr[idx] / arr[idx].max() * 100
        for i, val in zip(idx, x):
            w = min(dates[i].isocalendar()[1] - 1, 52); wk[w] += val; wc[w] += 1
            mon[dates[i].month - 1] += val; mc[dates[i].month - 1] += 1
    wk = np.divide(wk, wc, out=np.zeros(53), where=wc > 0); mon = np.divide(mon, mc, out=np.zeros(12), where=mc > 0)
    pk = int(wk.argmax()); nowk = TODAY.isocalendar()[1] - 1; cur = float(wk[nowk])
    ahead = (pk - nowk) % 52
    peak_day = TODAY + dt.timedelta(weeks=ahead)
    return {"yrs": yrs, "cur_pct": round(cur), "peak_date": f"{peak_day.month}월 {peak_day.day}일", "weeks_to_peak": ahead,
            "lift": round(float(wk.max()) / max(cur, 0.5), 1), "monthly_shape": [round(float(m)) for m in mon]}


def main():
    db = firestore.Client(project="itemscout-data-358206", database="trenddata")
    got = {g["keyword"]: {"monthly": g.get("monthly"), "prd_cnt": g.get("prd_cnt"), "image": g.get("image")} for g in enrich([{"keyword": k} for k in IS_KW])}
    sea = {k: season(db, k) for k in SEASON_KW}
    OUT.write_text(json.dumps({"asof": str(TODAY), "itemscout": got, "season": sea}, ensure_ascii=False, indent=1))
    for k, v in got.items(): print(f"  {k}: 월 {v['monthly']} · 상품 {v['prd_cnt']} · img {'O' if v['image'] else '-'}")
    for k, v in sea.items(): print(f"  [계절] {k}: {v and {x: v[x] for x in ['yrs','cur_pct','peak_date','weeks_to_peak','lift']}}")


if __name__ == "__main__":
    main()
