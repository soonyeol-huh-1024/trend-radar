"""셀러KIM 9호 숫자 고정: 아이템스카우트(월 검색·상품 수·대표 이미지) + 계절 곡선(naver_keyword_trend 9년).
한 호에서 쓰는 숫자는 모두 이 파일(issue09_data.json)에서 가져온다 (GUIDE '한 키워드에는 한 숫자만').
"""
import datetime as dt, json, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from google.cloud import firestore
sys.path.insert(0, str(Path(__file__).parent.parent))
from radar.common import enrich

OUT = Path(__file__).parent / "issue09_data.json"
TODAY = dt.date(2026, 10, 26)
IS_KW = ["카본매트", "일월카본매트", "귀뚜라미카본매트", "전기요", "전기장판", "온수매트", "보온물주머니", "핫팩", "온풍기", "욕실온풍기",
         "전기담요", "온열담요", "양모이불", "이서진양모이불", "치이카와", "먼작귀", "우사기", "모몽가", "쿠리만쥬", "랏코", "하치와레",
         "치이카와인형", "우사기인형", "치이카와팝콘통", "너구링", "너구리", "양파링", "금목서", "금목서묘목", "은목서", "갈옷",
         "롱패딩", "빼빼로", "초등책가방", "초등가방", "온천", "문풍지", "가계부", "대게", "냉풍기", "모기장", "튜브", "메디큐브", "361도", "워터파크",
         "캐리비안베이", "아이폰18", "아이폰18프로", "오가닉포에버", "휘태커스초콜릿", "스마트안경", "ai안경"]
SEASON_KW = ["카본매트", "전기요", "전기담요", "온열담요", "양모이불", "롱패딩", "빼빼로", "초등책가방", "초등가방", "온천", "하이원리조트", "문풍지", "가계부", "대게",
             "냉풍기", "모기장", "튜브", "모기퇴치기", "캐리비안베이"]


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
