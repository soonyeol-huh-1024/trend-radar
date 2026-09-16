"""
B→A 역방향 브리지: 해외에선 유행인데 한국은 아직 조용한 상품(수입 후보) 판정.

입력: import_map.csv (en_keyword, ko_keyword, source, overseas_signal, role)
한국 상태:
  - ItemScout 내부 API: 월간검색량(monthly.total)·네이버쇼핑 상품수(prdCnt)·1차 카테고리
    (쿠키는 worker/src/naver.ts 에서 런타임에 읽음 — 재하드코딩 금지)
  - 네이버 데이터랩: 3년 주간 상대추이(ratio) → 단계 판정
    (자격증명 Firestore gen-lang-client-0493835715/trend-checker/naver_api_keys)
단계:
  미도입   월검색 < LOW  (데이터랩 최근 8주 평균 ≤ 3년 최대의 30%)
  초기부상 LOW ≤ 월검색 < MID  이고 최근 8주 / 직전 26주 ≥ 1.5
  진행중   월검색 ≥ MID 이고 상승 중
  이미유행 월검색 ≥ MID 이고 최근 8주가 3년 최대의 50% 이상 (고원)
  식음     3년 최대 대비 최근 8주 < 50% 이고 최대가 12주 이전

사용: python import_candidates.py
출력: data/import_candidates.csv
"""
import json
import re
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from google.cloud import firestore

HERE = Path(__file__).parent
NAVER_TS = HERE.parent / "worker" / "src" / "naver.ts"
ITEMSCOUT_URL = "https://api.itemscout.io/api/keyword/data/list"
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
LOW, MID = 5_000, 30_000


def itemscout_cookie() -> str:
    m = re.search(r"'cookie':\s*'([^']+)'", NAVER_TS.read_text())
    if not m:
        raise SystemExit("naver.ts 에서 ItemScout 쿠키를 찾지 못함")
    return m.group(1)


def datalab_creds() -> tuple[str, str]:
    db = firestore.Client(project="gen-lang-client-0493835715", database="trend-checker")
    doc = next(iter(db.collection("naver_api_keys").order_by("req_num").limit(1).stream()), None)
    if doc is None:
        raise SystemExit("naver_api_keys 없음")
    d = doc.to_dict()
    return d["client_id"], d["client_secret"]


def itemscout(kw: str, cookie: str) -> dict:
    r = requests.post(ITEMSCOUT_URL, data={"keywords": kw}, timeout=20, headers={
        "content-type": "application/x-www-form-urlencoded", "origin": "https://itemscout.io",
        "referer": "https://itemscout.io/", "cookie": cookie,
        # python-requests 기본 UA 는 418 로 차단됨 → 브라우저 UA 필수
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"})
    d = ((r.json().get("data") or [{}])[0]) if r.ok else {}
    return {"monthly": (d.get("monthly") or {}).get("total"), "prd_cnt": d.get("prdCnt"),
            "nv_category": d.get("firstCategory")}


def datalab(kw: str, cid: str, csec: str) -> list[dict]:
    end = date.today()
    body = {"startDate": (end - timedelta(days=365 * 3)).isoformat(), "endDate": end.isoformat(),
            "timeUnit": "week", "keywordGroups": [{"groupName": kw, "keywords": [kw]}]}
    r = requests.post(DATALAB_URL, json=body, timeout=20, headers={
        "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec, "Content-Type": "application/json"})
    return (r.json().get("results") or [{}])[0].get("data", []) if r.ok else []


def stage(monthly: float | None, series: list[dict]) -> tuple[str, dict]:
    if not series:
        return "데이터없음", {}
    v = np.array([p["ratio"] for p in series], dtype=float)
    peak_i = int(v.argmax())
    recent, prior = v[-8:].mean(), (v[-34:-8].mean() if len(v) > 34 else np.nan)
    m = {"dl_peak_week": series[peak_i]["period"], "dl_recent_vs_peak": round(recent / max(v.max(), 1e-9), 2),
         "dl_recent_vs_prior": round(recent / prior, 2) if prior and prior > 0 else np.nan,
         "dl_first_nonzero": next((p["period"] for p in series if p["ratio"] > 0), None)}
    weeks_since_peak = len(v) - 1 - peak_i
    mo = monthly or 0
    if mo >= MID and m["dl_recent_vs_peak"] >= 0.5:
        s = "이미유행"
    elif mo >= MID and (m["dl_recent_vs_prior"] or 0) >= 1.3:
        s = "진행중"
    elif m["dl_recent_vs_peak"] < 0.5 and weeks_since_peak >= 12 and mo >= LOW:
        s = "식음"
    elif LOW <= mo < MID and (m["dl_recent_vs_prior"] or 0) >= 1.5:
        s = "초기부상"
    elif mo < LOW:
        s = "미도입"
    else:
        s = "정체"
    return s, m


def main() -> None:
    mp = pd.read_csv(HERE / "import_map.csv")
    cookie, (cid, csec) = itemscout_cookie(), datalab_creds()
    rows = []
    for r in mp.itertuples():
        # ko_keyword 는 '|' 로 동의어 여러 개 — 한국은 다른 단어를 쓸 수 있으므로 월검색 최대인 표기를 채택
        variants = [v.strip() for v in str(r.ko_keyword).split("|") if v.strip()]
        best, best_it = variants[0], {"monthly": None, "prd_cnt": None, "nv_category": None}
        for v in variants:
            it = itemscout(v, cookie)
            if (it["monthly"] or 0) > (best_it["monthly"] or 0):
                best, best_it = v, it
            time.sleep(0.2)
        dl = datalab(best, cid, csec)
        st, m = stage(best_it["monthly"], dl)
        rows.append({**r._asdict(), "ko_used": best, "n_variants": len(variants), **best_it, "stage": st, **m})
        time.sleep(0.3)
    res = pd.DataFrame(rows).drop(columns=["Index"])
    res.to_csv(HERE / "data" / "import_candidates.csv", index=False)
    pd.set_option("display.width", 240)
    cols = ["role", "en_keyword", "ko_used", "n_variants", "monthly", "prd_cnt", "stage",
            "dl_peak_week", "dl_recent_vs_peak", "dl_recent_vs_prior", "dl_first_nonzero"]
    for role in ("선례", "후보", "K원산"):
        print(f"\n=== {role} ===")
        print(res[res["role"] == role][cols].to_string(index=False))


if __name__ == "__main__":
    main()
