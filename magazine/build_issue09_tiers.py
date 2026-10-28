"""셀러KIM 9호 — 무료/플러스/프로 등급 미리보기 (비공개 검토용).

7호 등급판(build_issue07_tiers)의 표시 규칙·CSS·스크립트를 그대로 쓰고, 9호 문장·데이터만 바꾼다.
사용: python build_issue09_tiers.py → sellerkim_issue09_tiers.html
"""
import base64
import datetime as dt
import json
import re
from html import escape
from pathlib import Path

from build_issue07_tiers import BAND, CSS, JS, box, mark, n, spark, tbl
from build_issue09 import IMAGES
from issue09_free_rewrites import REWRITES

HERE = Path(__file__).parent
D = json.loads((HERE / "issue09_data.json").read_text())
PRO = json.loads((HERE / "issue09_pro.json").read_text())
IS, SEA, A = D["itemscout"], D["season"], PRO["amazon"]
NAMES = {"us": "미국", "uk": "영국", "de": "독일", "jp": "일본"}
VERSION = "v1.0"


def is_rows(keys):
    return [[k, n(IS[k]["monthly"]), n(IS[k]["prd_cnt"]), f'{IS[k]["monthly"] / max(IS[k]["prd_cnt"], 1):.2f}'] for k in keys if k in IS]


HEAT = [[NAMES[c], r, escape(k), n(s)] for c in ("de", "uk", "us") for r, k, s in A[c + "_heat"]]
BOXES = {
    "cover": box("난방용품 — 나라별 아마존 순위와 국내 매트 검색", "10월 23일 아마존 검색 순위표에 든 난방용품 전부와, 국내 쇼핑 검색의 매트·물주머니입니다.",
                 tbl(["나라", "순위", "검색어", "월 검색"], HEAT, {1, 3})
                 + tbl(["국내 검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["전기장판", "온수매트", "카본매트", "귀뚜라미카본매트", "일월카본매트", "보온물주머니", "온풍기"]), {1, 2, 3}),
                 ["난방용품_아마존4개국_52주.csv"]),
    "this-week": box(f"이번 주 위클리 키워드 {PRO['weekly_total']:,}개 중 상위 15", "본문은 상위 10개와 치이카와 친구들만 다룹니다. 프로에서는 전체 목록과 각 키워드의 3년 주간 추이를 받습니다.",
                     tbl(["순위", "키워드", "분류", "월 검색"], [[i + 1, k, c, n(s)] for i, (k, c, s) in enumerate(PRO["weekly_top"][:15])], {0, 3})
                     + tbl(["치이카와 친구들", "월 검색", "등록 상품", "검색÷상품"], is_rows(["치이카와", "우사기", "모몽가", "하치와레", "쿠리만쥬", "랏코", "치이카와인형", "우사기인형"]), {1, 2, 3}),
                     [f"위클리키워드_2026-10-26_{PRO['weekly_total']}개.csv", "주간추이_3년.csv"]),
    "brand": box("너구링 검색·상품", "새 과자 이름과 원래 라면 이름을 나란히 놓았습니다.",
                 tbl(["검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["너구링", "너구리", "양파링"]), {1, 2, 3}),
                 ["너구링_연관어_52주.csv"]),
    "dispatch": box("네 나라 아마존 검색 상위 (10월 23일)", "본문은 나라별 두세 개만 고릅니다. 프로에서는 나라별 상위 100개 키워드 전체를 받습니다.",
                    "".join(f"<h5>{NAMES[c]}</h5>" + tbl(["키워드", "카테고리", "월 검색"], [[escape(k), escape(cat), n(s)] for k, cat, s in A[c][:5]], {2}) for c in NAMES),
                    ["아마존_4개국_2026-10-23.csv"]),
    "word": box("금목서 연관 검색어", "나무 이름과 묘목, 비슷한 나무를 한 표에 놓았습니다.",
                tbl(["검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["금목서", "금목서묘목", "은목서"]), {1, 2, 3}),
                ["금목서_연관어_52주.csv"]),
    "forecast": box(f"계절성 DB — 이번 호 후보 {len(SEA)}개 전체", "5년 주간 기록으로 계산한 정점 시기와 지금 위치. 막대는 1~12월 평균 모양입니다.",
                    tbl(["키워드", "월별 모양", "지금(정점 대비)", "정점", "배수", "월 검색", "등록 상품"],
                        [[k, spark(v["monthly_shape"]), f'{v["cur_pct"]}%', v["peak_date"], f'{v["lift"]}배',
                          n((IS.get(k) or {}).get("monthly")), n((IS.get(k) or {}).get("prd_cnt"))] for k, v in SEA.items() if v], {2, 4, 5, 6}),
                    ["계절성DB_5년_전체.csv"]),
}
PLUS_CTA = {
    "cover": ("매트·물주머니 검색수·상품수 확인", "보온물주머니 검색수 →"),
    "this-week": ("TOP 10·치이카와 친구들 검색수 확인", "우사기 검색수 →"),
    "brand": ("너구링 검색수·상품수 확인", "너구링 검색수 →"),
    "word": ("금목서 검색수 확인", "금목서 검색수 →"),
    "forecast": ("초등책가방·롱패딩·온천 검색수 확인", "초등책가방 상품수 →"),
    "picks": ("문풍지·대게·가계부 검색수 확인", "문풍지 상품수 →"),
    "timing": ("냉풍기·모기장 검색수 확인", "냉풍기 상품수 →"),
    "followup": ("메디큐브·361도·치이카와팝콘통 검색수 확인", "361도 검색수 →"),
    "watching": ("관찰 품목 검색수 확인", "검색수 →"),
}
PRO_CTA = {"cover": "난방용품 나라별 데이터 보기", "this-week": f"위클리 키워드 {PRO['weekly_total']:,}개 전체 보기",
           "brand": "너구링 연관어 데이터 보기", "dispatch": "아마존 4개국 키워드 전체 보기",
           "word": "금목서 연관어 데이터 보기", "forecast": f"계절성 DB {len(SEA)}개 전체 보기"}


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
    html = (HERE / "issue09_template.html").read_text()
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
    head = head.replace("</style>", CSS + "</style>", 1).replace("<title>셀러KIM 제9호 · 10월 5주</title>", "<title>셀러KIM 9호 등급 미리보기</title>")
    html = head + body + tail + "\n" + JS
    for key, fname in IMAGES.items():
        html = html.replace("{{IMG_" + key + "}}", img(fname))
    return html


def main():
    out = HERE / "sellerkim_issue09_tiers.html"
    out.write_text(render(lambda f: "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / f).read_bytes()).decode()))
    print(f"{out.name} {out.stat().st_size / 1e6:.2f}MB · 바꾼 문장 {len(REWRITES)}개 · 프로 상자 {len(BOXES)}개")


if __name__ == "__main__":
    main()
