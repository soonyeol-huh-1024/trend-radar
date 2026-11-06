"""셀러KIM 10호 — 무료/플러스/프로 등급 미리보기 (비공개 검토용).

7호 등급판(build_issue07_tiers)의 표시 규칙·CSS·스크립트를 그대로 쓰고, 10호 문장·데이터만 바꾼다.
사용: python build_issue10_tiers.py → sellerkim_issue10_tiers.html
"""
import base64
import datetime as dt
import json
import re
from html import escape
from pathlib import Path

from build_issue07_tiers import BAND, CSS, JS, box, mark, n, spark, tbl
from build_issue10 import IMAGES
from issue10_free_rewrites import REWRITES

HERE = Path(__file__).parent
D = json.loads((HERE / "issue10_data.json").read_text())
PRO = json.loads((HERE / "issue10_pro.json").read_text())
IS, SEA, A = D["itemscout"], D["season"], PRO["amazon"]
NAMES = {"us": "미국", "uk": "영국", "de": "독일", "jp": "일본"}
VERSION = "v1.0"


def is_rows(keys):
    return [[k, n(IS[k]["monthly"]), n(IS[k]["prd_cnt"]), f'{IS[k]["monthly"] / max(IS[k]["prd_cnt"], 1):.2f}'] for k in keys if k in IS]


EMERG = [[NAMES[c], r, escape(k), n(s)] for c in ("uk", "de") for r, k, s in A[c + "_emerg"]]
BOXES = {
    "cover": box("비상용품 — 아마존 순위와 국내 검색", "10월 30일 영국·독일 아마존 검색 순위표에 든 비상용품 전부와, 국내 쇼핑 검색의 비상용품입니다.",
                 tbl(["나라", "순위", "검색어", "월 검색"], EMERG, {1, 3})
                 + tbl(["국내 검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["휴대용라디오", "생존배낭", "비상식량", "간이화장실", "휴대용화장실", "정수알약", "휴대용정수기", "캠핑스토브", "보조배터리", "구급함"]), {1, 2, 3}),
                 ["비상용품_아마존4개국_52주.csv"]),
    "this-week": box(f"이번 주 위클리 키워드 {PRO['weekly_total']:,}개 중 상위 15", "본문은 상위 10개와 브랜드 경량패딩만 다룹니다. 프로에서는 전체 목록과 각 키워드의 3년 주간 추이를 받습니다.",
                     tbl(["순위", "키워드", "분류", "월 검색"], [[i + 1, k, c, n(s)] for i, (k, c, s) in enumerate(PRO["weekly_top"][:15])], {0, 3})
                     + tbl(["경량패딩·후리스", "월 검색", "등록 상품", "검색÷상품"], is_rows(["경량패딩", "스파오경량패딩", "탑텐경량패딩", "유니클로경량패딩", "아이더경량패딩", "휠라경량패딩", "후리스", "스파오후리스", "유니클로후리스"]), {1, 2, 3}),
                     [f"위클리키워드_2026-11-02_{PRO['weekly_total']}개.csv", "주간추이_3년.csv"]),
    "brand": box("페이커우표 검색·상품", "검색 횟수와 그 이름으로 올라온 상품 수입니다.",
                 tbl(["검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["페이커우표"]), {1, 2, 3}),
                 ["페이커우표_연관어_52주.csv"]),
    "dispatch": box("네 나라 아마존 검색 상위 (10월 30일)", "본문은 나라별 두세 개만 고릅니다. 프로에서는 나라별 상위 100개 키워드 전체를 받습니다.",
                    "".join(f"<h5>{NAMES[c]}</h5>" + tbl(["키워드", "카테고리", "월 검색"], [[escape(k), escape(cat), n(s)] for k, cat, s in A[c][:5]], {2}) for c in NAMES),
                    ["아마존_4개국_2026-10-30.csv"]),
    "word": box("설아복숭아 연관 검색어", "품종 이름과 과일 이름을 한 표에 놓았습니다.",
                tbl(["검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["설아복숭아", "복숭아"]), {1, 2, 3}),
                ["설아복숭아_연관어_52주.csv"]),
    "forecast": box(f"계절성 DB — 이번 호 후보 {len(SEA)}개 전체", "5년 주간 기록으로 계산한 정점 시기와 지금 위치. 막대는 1~12월 평균 모양입니다.",
                    tbl(["키워드", "월별 모양", "지금(정점 대비)", "정점", "배수", "월 검색", "등록 상품"],
                        [[k, spark(v["monthly_shape"]), f'{v["cur_pct"]}%', v["peak_date"], f'{v["lift"]}배',
                          n((IS.get(k) or {}).get("monthly")), n((IS.get(k) or {}).get("prd_cnt"))] for k, v in SEA.items() if v], {2, 4, 5, 6}),
                    ["계절성DB_5년_전체.csv"]),
}
PLUS_CTA = {
    "cover": ("비상용품 검색수·상품수 확인", "정수알약 상품수 →"),
    "this-week": ("TOP 10·브랜드 경량패딩 검색수 확인", "스파오경량패딩 검색수 →"),
    "brand": ("페이커우표 검색수·상품수 확인", "페이커우표 검색수 →"),
    "word": ("설아복숭아 검색수 확인", "설아복숭아 검색수 →"),
    "forecast": ("트리·넥워머·과메기 검색수 확인", "과메기 검색수 →"),
    "picks": ("패딩부츠·곶감 검색수 확인", "곶감 상품수 →"),
    "timing": ("책가방·실내화·낮잠이불·강아지한복 검색수 확인", "낮잠이불 상품수 →"),
    "followup": ("너구링·쿠리만쥬 검색수 확인", "쿠리만쥬 상품수 →"),
}
PRO_CTA = {"cover": "비상용품 나라별 데이터 보기", "this-week": f"위클리 키워드 {PRO['weekly_total']:,}개 전체 보기",
           "brand": "페이커우표 연관어 데이터 보기", "dispatch": "아마존 4개국 키워드 전체 보기",
           "word": "설아복숭아 연관어 데이터 보기", "forecast": f"계절성 DB {len(SEA)}개 전체 보기"}


def free_swap(body: str) -> str:
    for orig, free in REWRITES:
        assert body.count(orig) == 1, f"원문 불일치: {orig[:40]}"
        body = body.replace(orig, f'<span class="v-p">{orig}</span><span class="v-f">{free}</span>')
    vals = [float(v.replace(",", "")) for v in re.findall(r'<div class="v"><b>([\d,]+)만</b>', body)]
    it = iter(vals)

    def rank(m):
        v = next(it)
        f = "<b>기준</b>1위" if v == vals[0] else f"<b>{round(v / vals[0] * 100)}%</b>1위 대비"
        return f'<div class="v"><span class="v-p">{m.group(1)}</span><span class="v-f">{f}</span></div>'
    return re.sub(r'<div class="v">(<b>[\d,]+만</b>한 달 검색)</div>', rank, body)


def add_cta(body: str) -> str:
    out, pos = [], 0
    for m in re.finditer(r'<article id="([^"]+)"', body):
        out.append(body[pos:m.start()])
        end = body.index("</article>", m.start())
        art, aid = body[m.start():end], m.group(1)
        if 'class="v-f"' in art and aid in PLUS_CTA:
            pm = re.search(r'<p[^>]*>(?:(?!</p>).)*class="v-f"(?:(?!</p>).)*</p>', art, flags=re.S)
            if pm:
                para = pm.group(0)
                art = art.replace(para, para[:-4] + f'<span class="only-free"><button type="button" class="cta-in" data-go="plus">{PLUS_CTA[aid][1]}</button></span></p>', 1)
            art += (f'<div class="cta only-free"><button type="button" data-go="plus">{PLUS_CTA[aid][0]}</button>'
                    '<span>플러스 · 월 9,900원</span></div>')
        if aid in BOXES:
            art = art.replace('<aside class="pro">', f'<div class="cta pro-up only-plus"><button type="button" data-go="pro">{PRO_CTA[aid]}</button>'
                              '<span>프로 · 표와 파일 · 월 99,000원부터</span></div><aside class="pro">', 1)
        out.append(art)
        pos = end
    out.append(body[pos:])
    return "".join(out)


def render(img) -> str:
    """등급판 HTML. img(파일명) → 이미지 src (아티팩트는 base64, 사이트는 URL)."""
    html = (HERE / "issue10_template.html").read_text()
    a, b = html.index('<header class="mast">'), html.index("<footer>")
    head, body, tail = html[:a], mark(free_swap(html[a:b])), html[b:]
    left = len(re.findall(r'class="abs"', re.sub(r'<span class="v-p">.*?</span><span class="v-f">', '', body, flags=re.S)))
    print("무료판에서 바뀌지 않고 남은 수치:", left)
    for aid, bx in BOXES.items():
        j = body.index("</article>", body.index(f'<article id="{aid}"'))
        body = body[:j] + bx + "\n" + body[j:]
    body = add_cta(body)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    assert body.count('<div class="meta">') == 1
    body = body.replace('<div class="meta">', f'<div class="meta"><span class="ver">등급 미리보기 {VERSION} · {stamp}</span><br>', 1)
    k = body.index("</header>") + len("</header>")
    body = body[:k] + "\n" + BAND + body[k:]
    head = head.replace("</style>", CSS + "</style>", 1).replace("<title>셀러KIM 제10호 · 11월 1주</title>", "<title>셀러KIM 10호 등급 미리보기</title>")
    html = head + body + tail + "\n" + JS
    for key, fname in IMAGES.items():
        html = html.replace("{{IMG_" + key + "}}", img(fname))
    return html


def main():
    out = HERE / "sellerkim_issue10_tiers.html"
    out.write_text(render(lambda f: "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / f).read_bytes()).decode()))
    print(f"{out.name} {out.stat().st_size / 1e6:.2f}MB · 바꾼 문장 {len(REWRITES)}개 · 프로 상자 {len(BOXES)}개")


if __name__ == "__main__":
    main()
