"""
주간 아마존 인사이트 작성용 브리프.

수집 원본(amazon_weekly/{cc}_{week})은 그대로 두고, 인사이트를 쓰기 전에 읽을
요약만 만든다. 두 가지 문제를 보정한다.

  A. 검색 랭킹이 너무 안 변함 — 최근 N주 중 EVERGREEN_MIN주 이상 등장한
     '붙박이'를 상시 카테고리로 분리하고, 신규·급등만 앞으로 낸다.
  C. 판매 랭킹이 노이즈로 너무 변함 — owala/amazon 처럼 같은 대상의 철자
     변형이 매주 다르게 잡히므로 대표 키워드로 묶어 합산한다.

사용: python amazon_brief.py [us|jp] [주차 YYYY-MM-DD, 생략 시 최신]
"""
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from google.cloud import firestore

DB = firestore.Client(project="gen-lang-client-0493835715", database="trend-checker")
N_WEEKS = 12          # 붙박이 판정 기간
EVERGREEN_MIN = 9     # N주 중 이 횟수 이상이면 붙박이
SIM = 0.75            # 1차: 철자 변형으로 볼 유사도
SIM2 = 0.68           # 2차: 지배 브랜드 토큰 대조(더 관대)
ANCHOR_MAXLEN = 9     # 대표 키워드 후보 최대 길이(정규화 후)


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣ぁ-んァ-ヶ一-龥]", "", str(s).lower())


def weeks(cc: str) -> list[str]:
    d = DB.collection("amazon_weekly").document(f"{cc}_weeks").get().to_dict() or {}
    return sorted(d.get("weeks", []))


def load(cc: str, wk: str) -> dict:
    return DB.collection("amazon_weekly").document(f"{cc}_{wk}").get().to_dict() or {}


def cluster(keywords: list[str]) -> dict[str, str]:
    """키워드 → 대표 키워드.

    1차: 짧고 자주 나오는 앵커를 포함/오타 유사도로 흡수.
    2차: 1차에서 3건 이상 모인 앵커를 '지배 브랜드'로 보고, 남은 단독 키워드를
         토큰 단위로 다시 대조한다. (`awalah water bottle` 처럼 오타 토큰이
         긴 키워드에 섞여 있으면 1차 전체 문자열 비교로는 걸리지 않는다.)
    """
    freq = Counter(norm(k) for k in keywords)
    anchors = sorted(
        (n for n in freq if 3 <= len(n) <= ANCHOR_MAXLEN),
        key=lambda n: (-freq[n], len(n)),
    )

    def match(n: str, pool: list[str], sim: float) -> str | None:
        hit = next((a for a in pool if a != n and a in n), None)
        if hit:
            return hit
        return next((a for a in pool
                     if abs(len(a) - len(n)) <= 3
                     and SequenceMatcher(None, a, n).ratio() >= sim), None)

    rep = {k: (match(norm(k), anchors, SIM) or norm(k)) for k in keywords if norm(k)}
    rep.update({k: k for k in keywords if not norm(k)})

    dominant = [a for a, c in Counter(rep.values()).items() if c >= 3]
    if dominant:
        for k, r in list(rep.items()):
            if r in dominant:
                continue
            toks = [norm(t) for t in re.split(r"[\s-]+", str(k)) if len(norm(t)) >= 4]
            hit = next((d for t in toks
                        for d in dominant
                        if d in t or SequenceMatcher(None, d, t).ratio() >= SIM2), None)
            if hit:
                rep[k] = hit

    # 대표 이름은 클러스터에서 가장 짧은 원본 키워드로
    members = defaultdict(list)
    for k, r in rep.items():
        members[r].append(k)
    label = {r: min(ms, key=len) for r, ms in members.items()}
    return {k: label[r] for k, r in rep.items()}


def main() -> None:
    cc = (sys.argv[1] if len(sys.argv) > 1 else "us").lower()
    ws = weeks(cc)
    wk = sys.argv[2] if len(sys.argv) > 2 else ws[-1]
    window = [w for w in ws if w <= wk][-N_WEEKS:]
    cur, prev = load(cc, wk), load(cc, window[-2]) if len(window) > 1 else (load(cc, wk), {})

    hist = {w: load(cc, w) for w in window}
    seen = Counter(x["keyword"] for w in window for x in hist[w].get("searchRanking", []))
    prank = {x["keyword"]: i + 1 for i, x in enumerate(prev.get("searchRanking", []))}
    search = cur.get("searchRanking", [])

    print(f"# {cc.upper()} {wk} 브리프  (붙박이 기준: 최근 {len(window)}주 중 {EVERGREEN_MIN}주+)\n")

    ever = [x for x in search if seen[x["keyword"]] >= EVERGREEN_MIN]
    fresh = [x for x in search if seen[x["keyword"]] < EVERGREEN_MIN]

    print(f"## 신규·비붙박이 검색 키워드 ({len(fresh)}/100)")
    print(f"  {'#':>3} {'키워드':<32}{'검색량':>11}  {'등장':>5}  변동   카테고리")
    for i, x in enumerate(search):
        if seen[x["keyword"]] >= EVERGREEN_MIN:
            continue
        k = x["keyword"]
        pr = prank.get(k)
        mv = "NEW" if pr is None else (f"↑{pr - (i+1)}" if pr > i + 1 else (f"↓{(i+1)-pr}" if pr < i + 1 else "-"))
        print(f"  {i+1:>3} {k[:31]:<32}{x.get('search_cnt',0):>11,}  {seen[k]:>2}/{len(window)}주  {mv:<5}  {str(x.get('category'))[:20]}")

    print(f"\n## 급등 (전주 대비 10계단 이상 상승, 붙박이 포함)")
    ups = []
    for i, x in enumerate(search):
        pr = prank.get(x["keyword"])
        if pr and pr - (i + 1) >= 10:
            ups.append((pr - (i + 1), i + 1, x))
    for d, r, x in sorted(ups, reverse=True)[:12]:
        print(f"  ↑{d:<3} {r:>3}위  {x['keyword'][:30]:<32}{x.get('search_cnt',0):>11,}  ({seen[x['keyword']]}/{len(window)}주)")
    if not ups:
        print("  (없음)")

    print(f"\n## 상시 카테고리 — 붙박이 {len(ever)}개 (인사이트에서 반복 서술 불필요)")
    print("  " + ", ".join(f"{x['keyword']}({i+1}위)" for i, x in enumerate(search) if seen[x["keyword"]] >= EVERGREEN_MIN)[:1200])

    # C. 판매 랭킹 정규화
    sales = cur.get("salesRanking", [])
    rep = cluster([x["keyword"] for x in sales])
    grp = defaultdict(lambda: {"sales": 0, "revenue": 0.0, "members": [], "best": 999})
    for i, x in enumerate(sales):
        g = grp[rep[x["keyword"]]]
        g["sales"] += x.get("sales", 0) or 0
        g["revenue"] += x.get("revenue", 0) or 0
        g["members"].append(x["keyword"])
        g["best"] = min(g["best"], i + 1)

    print(f"\n## 판매 랭킹 정규화 — {len(sales)}개 → {len(grp)}개 클러스터")
    print(f"  {'대표':<26}{'합산판매':>10}{'변형':>5}  최고순위  멤버 예시")
    for name, g in sorted(grp.items(), key=lambda kv: -kv[1]["sales"])[:15]:
        ex = ", ".join(g["members"][:3])[:58]
        print(f"  {name[:25]:<26}{g['sales']:>10,}{len(g['members']):>4}개  {g['best']:>4}위  {ex}")


if __name__ == "__main__":
    main()
