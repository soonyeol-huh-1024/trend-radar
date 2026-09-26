"""트렌드레이더 — 워치리스트 이력 적재와 신호 판정.

셀러가 등록한 키워드만 매주 스냅샷해 두고, 지난주와 비교해 신호를 만든다.
전체 4,678개를 매주 쌓으면 무겁고 대부분 안 쓴다 — 담긴 것만 쌓는다.

  radar_watch/{uid}            registered[] : 등록한 키워드
  radar_history/{키워드}/weeks/{주}  monthly · prd_cnt · ratio

쓰기:
  python3 -m radar.watch snapshot          이번 주 스냅샷 (등록된 키워드 전체)
  python3 -m radar.watch signals           지난주 대비 신호 출력
  python3 -m radar.watch add <uid> <키워드…>

신호 이름은 전략 문서 v1(2026-09-27)의 한국어 상태와 타이밍으로 보여 준다.
규칙 네 개는 그대로 두고 표시만 바꿨다. '빠르게 커지는 중'·'많이 퍼짐'은
여러 주 가속도와 절대 규모가 필요해 아직 판정하지 않는다.
"""
from __future__ import annotations

import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor

from google.cloud import firestore

from . import common

PROJECT, DATABASE = "gen-lang-client-0493835715", "trend-checker"

WATCH, HISTORY = "radar_watch", "radar_history"

# 신호 판정 기준 — 4호 치이카와 사례(상품 19배, 검색 +4%)가 '자리가 채워지는 중'에 걸린다
FILLING_PRD = 0.30      # 상품 수가 이만큼 늘고
FILLING_SEARCH = 0.15   # 검색은 이보다 덜 움직이면 → 경쟁자가 들어온 것
COOLING_SEARCH = -0.25  # 검색이 이만큼 빠지면 → 수요가 식는 것
OPENING_SEARCH = 0.30   # 검색이 이만큼 늘고
OPENING_PRD = 0.15      # 상품은 이보다 덜 늘면 → 수요가 먼저 온 것
SQUEEZE_PRD = 0.20      # 상품은 이만큼 느는데
SQUEEZE_SEARCH = -0.10  # 검색은 이만큼 빠지면 → 양쪽이 나빠진다 (가장 나쁜 조합)


# 내부 규칙 → (사용자에게 보이는 상태, 타이밍). 전략 문서 §03 표기.
LIFECYCLE = {
    "SQUEEZE": ("식는 중",   "늦을 수 있음"),   # 공급은 늘고 수요는 빠진다 — 가장 나쁜 조합
    "FILLING": ("경쟁 심함", "늦을 수 있음"),   # 수요는 그대로인데 공급이 몰린다 (치이카와 48 → 908)
    "COOLING": ("식는 중",   "조금 더 보기"),   # 수요가 빠진다
    "OPENING": ("막 뜨는 중", "지금 볼만함"),   # 수요가 공급보다 먼저 왔다. 신호가 하나뿐이라 '진입 타이밍'까지는 아니다
}


def db() -> firestore.Client:
    return firestore.Client(project=PROJECT, database=DATABASE)


def this_week(today: dt.date | None = None) -> str:
    """주차 키는 그 주 월요일(YYYY-MM-DD). 주간 배치가 월요일에 돈다."""
    d = today or dt.date.today()
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def watched(client: firestore.Client) -> dict[str, list[str]]:
    """키워드 → 그 키워드를 등록한 uid 목록. 중복 조회를 막는다."""
    out: dict[str, list[str]] = {}
    for doc in client.collection(WATCH).stream():
        uid = doc.id
        for kw in (doc.to_dict() or {}).get("registered", []):
            out.setdefault(kw, []).append(uid)
    return out


def snapshot(week: str | None = None, workers: int = 4) -> int:
    """등록된 키워드의 이번 주 지표를 ItemScout 에서 받아 적재한다."""
    client, wk = db(), week or this_week()
    kws = sorted(watched(client))
    if not kws:
        print("등록된 키워드가 없습니다.")
        return 0
    ck = common.cookie()

    def one(kw: str) -> tuple[str, dict]:
        d = common.itemscout(kw, ck)
        m, p = d.get("monthly"), d.get("prd_cnt")
        return kw, {
            "monthly": m, "prd_cnt": p,
            "ratio": round(m / p, 2) if (m and p) else None,
            "nv_cat": d.get("nv_cat"), "fetchedAt": dt.datetime.now(dt.timezone.utc),
        }

    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, kws))

    batch, n = client.batch(), 0
    for kw, rec in rows:
        if rec["monthly"] is None and rec["prd_cnt"] is None:
            continue                                   # 조회 실패는 빈 주로 남기지 않는다
        batch.set(client.collection(HISTORY).document(kw).collection("weeks").document(wk), rec)
        n += 1
        if n % 400 == 0:
            batch.commit(); batch = client.batch()
    batch.commit()
    print(f"{wk} 스냅샷 {n}/{len(kws)}건")
    return n


def _change(now: float | None, before: float | None) -> float | None:
    if not before or now is None:
        return None
    return (now - before) / before


def judge(cur: dict, prev: dict) -> tuple[str, str] | None:
    """두 주를 비교해 (규칙 ID, 설명) 을 낸다. 걸리는 게 없으면 None. 표시는 LIFECYCLE 로."""
    ds = _change(cur.get("monthly"), prev.get("monthly"))
    dp = _change(cur.get("prd_cnt"), prev.get("prd_cnt"))
    pct = lambda v: f"{v * 100:+.0f}%"

    # 순서가 중요하다. '상품 늘고 검색 빠짐'은 둘 중 아무 규칙에도 안 걸려 조용히 넘어갔었다
    # (오디세이책: 상품 +34%, 검색 -19%). 가장 나쁜 조합이므로 맨 앞에서 잡는다.
    if (dp is not None and dp >= SQUEEZE_PRD) and (ds is not None and ds <= SQUEEZE_SEARCH):
        return ("SQUEEZE",
                f"등록 상품은 {prev['prd_cnt']:,} → {cur['prd_cnt']:,}개({pct(dp)})로 느는데 "
                f"검색은 {prev['monthly']:,} → {cur['monthly']:,}번({pct(ds)})으로 빠집니다. "
                f"공급은 늘고 수요는 식는 구간입니다.")
    if dp is not None and dp >= FILLING_PRD and (ds is None or abs(ds) < FILLING_SEARCH):
        return ("FILLING",
                f"등록 상품 {prev['prd_cnt']:,} → {cur['prd_cnt']:,}개({pct(dp)})인데 "
                f"검색은 {pct(ds) if ds is not None else '변화 없음'}입니다. 경쟁자가 들어오고 있습니다.")
    if ds is not None and ds <= COOLING_SEARCH:
        return ("COOLING",
                f"한 달 검색 {prev['monthly']:,} → {cur['monthly']:,}번({pct(ds)}).")
    if ds is not None and ds >= OPENING_SEARCH and (dp is None or dp < OPENING_PRD):
        return ("OPENING",
                f"검색이 {pct(ds)} 올랐는데 상품은 {pct(dp) if dp is not None else '그대로'}입니다. "
                f"수요가 공급보다 먼저 왔습니다.")
    return None


def signals(week: str | None = None) -> list[dict]:
    """이번 주와 직전 스냅샷을 비교해 신호가 걸린 것만 돌려준다."""
    client, wk = db(), week or this_week()
    out: list[dict] = []
    for kw, uids in sorted(watched(client).items()):
        # 키워드당 주차 문서는 많아야 수십 개다. 색인을 만들 만큼이 아니라 받아서 정렬한다.
        weeks = client.collection(HISTORY).document(kw).collection("weeks")
        docs = {d.id: d.to_dict() for d in weeks.stream()}
        if wk not in docs or len(docs) < 2:
            continue
        prev_key = sorted(k for k in docs if k < wk)[-1:]
        if not prev_key:
            continue
        hit = judge(docs[wk], docs[prev_key[0]])
        if hit:
            state, timing = LIFECYCLE[hit[0]]
            out.append({"keyword": kw, "uids": uids, "week": wk, "prevWeek": prev_key[0],
                        "rule": hit[0], "state": state, "timing": timing, "detail": hit[1]})
    return out


def add(uid: str, *keywords: str) -> None:
    client = db()
    ref = client.collection(WATCH).document(uid)
    cur = (ref.get().to_dict() or {}).get("registered", [])
    merged = list(dict.fromkeys([*cur, *keywords]))
    ref.set({"registered": merged, "updatedAt": dt.datetime.now(dt.timezone.utc)}, merge=True)
    print(f"{uid}: {len(merged)}개 등록 (+{len(merged) - len(cur)})")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "signals"
    if cmd == "snapshot":
        snapshot()
    elif cmd == "add":
        add(sys.argv[2], *sys.argv[3:])
    else:
        rows = signals()
        if not rows:
            print("걸린 신호가 없습니다.")
        for r in rows:
            print(f"[{r['state']} · {r['timing']}] {r['keyword']}\n    {r['detail']}")


if __name__ == "__main__":
    main()
