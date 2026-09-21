"""셀러KIM 문장 다듬기 — OpenRouter / upstage/solar-pro4.

한 문단씩 보내 어투와 어색한 문장만 고친다. 숫자·사실·태그는 건드리지 않는다.
고친 결과는 바로 반영하지 않고 diff 로 보여 준 뒤, --apply 를 줘야 파일에 쓴다.

  python3 polish.py issue04_template.html            # 어투·문장 다듬기 미리보기
  python3 polish.py issue04_template.html --spacing   # 맞춤법·띄어쓰기만
  python3 polish.py issue04_template.html --apply     # 실제 반영
  python3 polish.py issue04_template.html --limit 5   # 앞 5문단만 시험
"""
from __future__ import annotations

import json, os, re, subprocess, sys, tempfile, pathlib, difflib

HERE = pathlib.Path(__file__).parent
MODEL = os.environ.get("POLISH_MODEL", "upstage/solar-pro4")
URL = "https://openrouter.ai/api/v1/chat/completions"

# 고칠 대상: 본문 문단과 소제목. 표·게이지·캡션 안의 숫자 덩어리는 건드리지 않는다.
TARGET = re.compile(r'<p(?: class="(?:lead|deck|pull)")?>(.+?)</p>', re.S)

SYSTEM = """너는 한국어 잡지 '셀러KIM'의 교열자다. 문장을 다듬되 다음을 반드시 지켜라.

■ 절대 바꾸지 말 것
- 숫자, 날짜, 고유명사, 통계치 (예: 6,450번 / 908개 / +143.4% / 2019년 7월)
- HTML 태그와 속성. <b>, <span class="hl">, <span class="mono"> 등은 개수·위치·속성을 그대로 유지한다.
- 사실 관계. 없는 내용을 추가하거나 있는 내용을 빼지 않는다.

■ 다듬을 것
- 어투: 기본은 '~습니다'. 사실을 말할 땐 '~습니다', 글쓴이의 반응이나 생각엔 '~요'를 섞어 딱딱함을 푼다.
- 가르치거나 지시하지 않는다. '~하세요', '~해야 합니다', '진입 적기입니다' 같은 말은 쓰지 않는다.
- 사물을 의인화하지 않는다. ('한 숫자가 걸렸습니다' → '이상한 숫자가 하나 있었습니다')
- '물건' 남발을 피하고 '상품'을 쓴다. '우리/우리나라' 대신 '한국'.
- 뜻이 흐릿한 문학적 마무리를 피한다.
- 소리 내 읽어 숨이 걸리는 문장을 끊거나 어순을 바꾼다.

■ 출력
- 고친 문단 본문만 출력한다. 설명, 따옴표, 머리말, 코드펜스를 붙이지 않는다.
- 고칠 데가 없으면 입력을 그대로 출력한다."""


SPACING = """너는 한국어 교정 전문가다. 아래 문단의 **맞춤법과 띄어쓰기만** 바로잡아라.

■ 절대 바꾸지 말 것
- 문장 구조, 낱말 선택, 어투, 문장 순서. 표현을 '더 좋게' 고치지 마라.
- 숫자, 날짜, 고유명사, 통계치.
- HTML 태그와 속성. 개수·위치·속성을 그대로 둔다.

■ 볼 것 (틀린 것만 고친다)
- 의존명사는 띄어 쓴다: 할 수 있다 / 아는 것 / 떠날 때 / 그럴 뿐 / 아는 만큼 / 하는 데
- 단위명사는 앞말과 띄어 쓴다: 한 달 / 세 배 / 여섯 개 / 3,550번 / 2주 뒤
- 조사·어미는 앞말에 붙여 쓴다: 상품보다 / 검색만 / 올라왔습니다
- 한 낱말로 굳은 말은 붙여 쓴다: 몇천 / 이번 주(x 이번주) / 지난해 / 이때
- 보조용언은 띄어 씀을 원칙으로 한다: 올라와 있습니다 / 봐 주는 것
- '안', '못'은 부사일 때 띄어 쓴다: 안 붙는다 / 못 판다

■ 출력
- 고친 문단 본문만 출력한다. 설명·따옴표·코드펜스를 붙이지 않는다.
- 틀린 데가 없으면 입력을 글자 하나 다르지 않게 그대로 출력한다."""


def key() -> str:
    """환경변수 → 저장소 루트의 .openrouter(키 한 줄) → trend_radar/.env 순으로 찾는다."""
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    plain = HERE.parent.parent / ".openrouter"          # 키만 한 줄 적힌 파일
    if plain.exists():
        v = plain.read_text().strip()
        if v:
            return v.split("=")[-1].strip().strip("\"'")
    env = HERE.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            n, _, v = line.partition("=")
            if n.strip() == "OPENROUTER_API_KEY" and v.strip():
                return v.strip().strip("\"'")
    raise SystemExit("키가 없습니다 — 저장소 루트 .openrouter 또는 trend_radar/.env 를 확인하세요.")


def ask(text: str, system: str = SYSTEM) -> str:
    body = {"model": MODEL, "temperature": 0.3,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": text}]}
    req = tempfile.mktemp(suffix=".json"); out = tempfile.mktemp(suffix=".json")
    pathlib.Path(req).write_text(json.dumps(body, ensure_ascii=False))
    subprocess.run(["curl", "-s", "-X", "POST", URL,
                    "-H", f"Authorization: Bearer {key()}",
                    "-H", "Content-Type: application/json",
                    "--data-binary", "@" + req, "-o", out], check=True, timeout=180)
    d = json.loads(pathlib.Path(out).read_text())
    if "choices" not in d:
        raise RuntimeError(str(d)[:200])
    return d["choices"][0]["message"]["content"].strip()


def protected(src: str) -> list[str]:
    """검색 키워드는 띄어쓰기를 손대면 안 된다 — 네이버에서 그 문자열 그대로 조회한 값이라
    '경량패딩'을 '경량 패딩'으로 띄우면 기사에 적힌 숫자와 어긋난다.
    지면에서 키워드로 쓰인 자리(mono 스팬, 순위표 이름, 예보 카드)를 모아 둔다."""
    out: set[str] = set()
    for pat in (r'<span class="mono[^"]*">([^<]+)</span>',
                r'<div class="b"><b>([^<]+)</b>',
                r'<div class="w">[^<]*</div><b>([^<]+)</b>'):
        for m in re.findall(pat, src):
            t = m.strip()
            if t and " " not in t and len(t) >= 3:
                out.add(t)
    out |= {"경량패딩", "할로윈코스튬", "스파오경량패딩", "할로윈의상", "노스페이스경량패딩",
            "살로몬경량패딩", "네파키즈패딩", "탑텐키즈바람막이", "베베드피노바람막이",
            "아기바람막이", "여아바람막이", "주니어바람막이", "키즈바람막이", "바람막이여성",
            "치이카와", "미리캔버스", "오디세이책", "코르티솔", "대맛조개", "문어괄사",
            "유니클로후리스블루종", "갤럭시폴드8", "아이폰18", "롯데시네마", "스파이더맨"}
    return sorted(out, key=len, reverse=True)


def tags(s: str) -> list[str]:
    """태그 구성이 그대로인지 확인할 지문."""
    return re.findall(r"<[^>]+>", s)


def numbers(s: str) -> list[str]:
    return re.findall(r"[\d,]+(?:\.\d+)?%?", re.sub(r"<[^>]+>", "", s))


def main() -> None:
    path = HERE / sys.argv[1]
    apply = "--apply" in sys.argv
    mode = SPACING if "--spacing" in sys.argv else SYSTEM
    what = "띄어쓰기" if "--spacing" in sys.argv else "문장"
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0

    src = path.read_text()
    keep = protected(src)
    hits = list(TARGET.finditer(src))
    if limit:
        hits = hits[:limit]

    changed, skipped, out = 0, [], src
    for i, m in enumerate(hits, 1):
        before = m.group(1)
        if len(re.sub(r"<[^>]+>", "", before)) < 25:      # 짧은 줄은 건드리지 않는다
            continue
        try:
            hint = [k for k in keep if k in before]
            sysmsg = mode if not hint else (
                mode + "\n\n■ 아래 낱말은 검색 키워드다. 띄어쓰기를 바꾸지 말고 글자 그대로 둬라.\n"
                + ", ".join(hint[:15]))
            after = ask(before, sysmsg)
        except Exception as e:
            skipped.append((i, f"호출 실패: {e}")); continue
        if after == before:
            continue
        if tags(after) != tags(before):
            skipped.append((i, "태그가 바뀌어 버림")); continue
        if numbers(after) != numbers(before):
            skipped.append((i, "숫자가 바뀌어 버림")); continue
        broke = [k for k in keep if k in before and k not in after]
        if broke:
            skipped.append((i, f"검색 키워드가 쪼개짐: {', '.join(broke[:3])}")); continue
        if mode is SPACING and before.replace(" ", "") != after.replace(" ", ""):
            skipped.append((i, "띄어쓰기 말고 다른 글자가 바뀜")); continue
        changed += 1
        print(f"\n── {i}번째 문단 ──")
        for line in difflib.unified_diff([before], [after], lineterm="", n=0):
            if line.startswith(("-", "+")) and not line.startswith(("---", "+++")):
                print(("  빼고: " if line[0] == "-" else "  넣고: ") + line[1:].strip()[:300])
        out = out.replace(before, after, 1)

    print(f"\n[{what}] 대상 {len(hits)}문단 · 고침 {changed} · 건너뜀 {len(skipped)}")
    for i, why in skipped:
        print(f"  {i}번째: {why}")
    if apply and changed:
        path.write_text(out)
        print(f"{path.name} 에 반영했습니다.")
    elif changed:
        print("미리보기만 했습니다. 반영하려면 --apply 를 붙이세요.")


if __name__ == "__main__":
    main()
