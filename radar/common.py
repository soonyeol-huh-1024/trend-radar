"""셀러킴 레이더 공통 유틸 — 데이터 로딩, ItemScout 경쟁도 조회, 공통 필터.

경쟁도(prdCnt)를 붙이는 이유: 성장 배수만 보면 '남성패딩'(등록 상품 388만)처럼
누구나 아는 대명사가 상위를 덮는다. 실제 가치는 검색 대비 등록 상품이 적은 쪽에 있다.
"""
from __future__ import annotations

import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
NAVER_TS = ROOT.parent / "worker" / "src" / "naver.ts"
ITEMSCOUT_URL = "https://api.itemscout.io/api/keyword/data/list"

# python-requests 기본 UA 는 418 로 차단됨 → 브라우저 UA 필수
HDRS = {
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://itemscout.io", "referer": "https://itemscout.io/",
    "user-agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"),
}

# 네이버쇼핑에서 파는 물건이 아니어서 prdCnt 가 낮은 것들 — 비율을 상품 근거로 쓰면 안 된다.
# 이걸 안 거르면 '롯데시네마'(검색 156만 / 상품 583개) 같은 게 비율 상위를 덮는다.
EXPERIENCE_HINTS = ("입장권", "이용권", "자유이용", "연간회원", "예매", "관람권", "숙박권",
                    "등산코스", "여행코스", "맛집", "축제", "전시", "공연", "뮤지컬", "콘서트",
                    "워터파크", "워터월드", "워터피아", "스파비스", "아쿠아리움", "리조트",
                    "시네마", "메가박스", "cgv", "온천", "펜션", "수목원", "놀이공원")
EXPERIENCE_CATS = ("여가/생활편의",)


def is_experience(keyword: str, cat_top: str | None = None, prd_cnt: int | None = None) -> bool:
    """네이버쇼핑 상품이 아닌 경험재인가. 단어 힌트 + 카테고리·상품수 조합으로 판정."""
    if any(h in keyword.lower() for h in EXPERIENCE_HINTS):
        return True
    # 여가/생활편의 카테고리에서 등록 상품이 극히 적으면 티켓·시설일 확률이 높다
    return (cat_top in EXPERIENCE_CATS) and (prd_cnt or 0) < 3_000


def cookie() -> str:
    m = re.search(r"'cookie':\s*'([^']+)'", NAVER_TS.read_text())
    if not m:
        raise SystemExit("naver.ts 에서 ItemScout 쿠키를 찾지 못함")
    return m.group(1)


def itemscout(kw: str, ck: str) -> dict:
    """키워드 1건의 월 검색수·등록 상품 수·카테고리·대표 이미지."""
    try:
        r = requests.post(ITEMSCOUT_URL, data={"keywords": kw}, timeout=20,
                          headers={**HDRS, "cookie": ck})
        d = (r.json().get("data") or [{}])[0] if r.ok else {}
    except Exception:
        d = {}
    return {"monthly": (d.get("monthly") or {}).get("total"), "prd_cnt": d.get("prdCnt"),
            "nv_cat": d.get("firstCategory"), "image": d.get("image")}


def enrich(rows: list[dict], key: str = "keyword", workers: int = 4) -> list[dict]:
    """rows 각각에 ItemScout 지표를 병렬로 붙이고 수요/공급 비율을 계산한다."""
    ck = cookie()

    def one(r: dict) -> dict:
        out = {**r, **itemscout(r[key], ck)}
        time.sleep(0.05)
        mo, pc = out.get("monthly"), out.get("prd_cnt")
        out["ratio"] = round(mo / pc, 2) if mo and pc else None
        out["is_experience"] = is_experience(r[key], r.get("cat_top"), out.get("prd_cnt"))
        return out

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, rows))


def load_naver() -> list[dict]:
    """주간 네이버 키워드 long 포맷 (week, keyword, search_cnt, mom/qoq/yoy, kw_type …)."""
    rows = list(csv.DictReader(open(DATA / "cand_naver.csv")))
    for r in rows:
        for c in ("search_cnt", "mom", "qoq", "yoy", "growth1m", "growth3m"):
            try:
                r[c] = float(r[c]) if r.get(c) not in (None, "", "None") else None
            except ValueError:
                r[c] = None
    return rows


def load_tiktok() -> list[dict]:
    rows = list(csv.DictReader(open(DATA / "cand_tiktok.csv")))
    for r in rows:
        r["views_total"] = int(float(r["views_total"] or 0))
    return rows


def load_amazon() -> list[dict]:
    return list(csv.DictReader(open(DATA / "cand_amazon_bq.csv")))


def weeks_of(rows: list[dict], col: str = "week") -> list[str]:
    return sorted({r[col] for r in rows if r.get(col)})


def series(rows: list[dict], kw: str) -> list[tuple[str, float]]:
    """한 키워드의 (주차, 검색수) 시계열 — 오래된 → 최신."""
    s = [(r["week"], r["search_cnt"]) for r in rows
         if r["keyword"] == kw and r["search_cnt"] is not None]
    return sorted(s)


def write(name: str, rows: list[dict], cols: list[str]) -> Path:
    OUT.mkdir(exist_ok=True)
    p = OUT / name
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  → {p.relative_to(ROOT)} ({len(rows)}행)")
    return p


def dump_json(name: str, obj) -> Path:
    OUT.mkdir(exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    print(f"  → {p.relative_to(ROOT)}")
    return p
