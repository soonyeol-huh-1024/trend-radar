# -*- coding: utf-8 -*-
"""한 호 안에서 같은 키워드가 서로 다른 숫자를 달고 있는지 찾는다."""
import re, sys, pathlib, collections

def check(path):
    src = pathlib.Path(path).read_text()
    txt = re.sub(r'<[^>]+>', ' ', src)
    txt = re.sub(r'\s+', ' ', txt)

    # 굵게·mono·표 이름으로 쓰인 낱말을 키워드 후보로 모은다
    cands = set()
    for pat in (r'<span class="mono[^"]*">([^<]+)</span>',
                r'<div class="b"><b>([^<]+)</b>',
                r'<h3[^>]*>([^<—]+)',
                r'<b>([가-힣A-Za-z0-9]{3,20})</b>'):
        for m in re.findall(pat, src):
            t = m.strip().rstrip('—·').strip()
            if 2 < len(t) < 22 and not re.search(r'[\d%]', t):
                cands.add(t)

    hits = collections.defaultdict(set)
    for kw in cands:
        # "키워드 ... 숫자(만/번/개)" 형태만 — 40자 이내로 가깝게 붙은 것
        for m in re.finditer(re.escape(kw) + r'[^가-힣A-Za-z]{0,6}(?:을|를|은|는|이|가|도|만)?[^<]{0,34}?(\d[\d,]*(?:만|억)?)\s*(번|개)', txt):
            hits[kw].add((m.group(1), m.group(2)))

    bad = {k: v for k, v in hits.items() if len({x for x, u in v if u == '번'}) > 1 or len({x for x, u in v if u == '개'}) > 1}
    print(f"\n===== {path} =====")
    print(f"  검사한 키워드 {len(cands)}개 · 숫자가 붙은 것 {len(hits)}개")
    if not bad:
        print("  ✅ 한 키워드에 두 숫자가 붙은 곳 없음")
    for k, v in sorted(bad.items()):
        print(f"  ⚠ {k}: {sorted(v)}")

    # 연도 계산 검증
    print("  — 연도가 나오는 문장 —")
    for m in re.finditer(r'[^.!?]*\b(19|20)\d{2}년[^.!?]*[.!?]', txt):
        t = m.group(0).strip()
        if re.search(r'(스물|서른|열|스무|[한두세네다섯여섯일곱여덟아홉]) ?해|[0-9]+ ?년 ?(만|째|된)', t):
            print(f"     {t[:150]}")

for p in sys.argv[1:]:
    check(p)
