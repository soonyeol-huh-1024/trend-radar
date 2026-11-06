"""셀러KIM 10호 숫자 고정: 아이템스카우트(월 검색·상품 수·대표 이미지) + 계절 곡선(naver_keyword_trend 9년).
한 호에서 쓰는 숫자는 모두 이 파일(issue10_data.json)에서 가져온다 (GUIDE '한 키워드에는 한 숫자만').
"""
import datetime as dt, json, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from google.cloud import firestore
sys.path.insert(0, str(Path(__file__).parent.parent))
from radar.common import enrich

OUT = Path(__file__).parent / "issue10_data.json"
TODAY = dt.date(2026, 11, 2)
IS_KW = ['생존배낭', '비상식량', '비상용품', '간이화장실', '휴대용화장실', '비상용화장실', '휴대용라디오', '라디오', '손전등', '랜턴', '생수', '보존수', '정수필터', '휴대용정수기', '정수알약', '캠핑스토브', '부탄가스', '보조배터리', '양초', '구급함', '경량패딩', '탑텐경량패딩', '스파오경량패딩', '유니클로경량패딩', '탑텐', '스파오', '후리스', '스파오후리스', '유니클로후리스', '아이더경량패딩', '휠라경량패딩', 'k2알파카', '너구링', '너구리', '쿠리만쥬', '설아복숭아', '복숭아', '과메기', '굴', '절임배추', '페이커우표', '휘태커스초콜릿', '선크림', '틴티드선크림', '톤업선크림', '메디큐브', '크리스마스트리', '크리스마스조명', '핫팩', '가습기', '수능시계', '연하장', '탁상달력', '귤', '방어', '대방어', '스키장', '눈썰매장', '패딩부츠', '선풍기', '래쉬가드', '수영복', '아이스박스', '쿨토시', '모기퇴치기', '할로윈의상', '캐리비안베이', '아이폰18프로', '빼빼로', '샌들', '휴대용선풍기', '비치타올', '곶감', '방한화', '넥워머', '손선풍기', '워터슈즈', '수면양말', '온풍기', '전기히터', '유니클로', '무신사', '치이카와', '롯데시네마', '클로드', '29cm', '뉴발란스', '먼작귀', '캠핑랜턴', '라디오손전등', '비상라디오']
SEASON_KW = ['크리스마스트리', '크리스마스조명', '절임배추', '과메기', '굴', '방어', '대방어', '귤', '핫팩', '가습기', '수능시계', '연하장', '탁상달력', '스키장', '눈썰매장', '패딩부츠', '롱패딩', '경량패딩', '후리스', '선풍기', '래쉬가드', '수영복', '아이스박스', '쿨토시', '선크림', '모기퇴치기', '할로윈의상', '빼빼로', '생존배낭', '비상식량', '손전등', '생수', '캐리비안베이', '복숭아', '설아복숭아', '곶감', '방한화', '넥워머', '샌들', '휴대용선풍기', '비치타올', '워터슈즈', '수면양말', '온풍기']


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
