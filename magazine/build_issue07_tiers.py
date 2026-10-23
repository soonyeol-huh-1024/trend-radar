"""셀러KIM 7호 — 무료/플러스/프로 등급 미리보기 (비공개 검토용).

issue07_template.html 을 그대로 두고 사본에서:
  ① 절대 수치(검색 횟수·상품 수)를 <span class="abs"> 로 표시 → 무료에서 ██,███ 로 가림
  ② 지난 호 링크(.backissue)는 무료에서 잠금
  ③ 프로 전용 데이터 상자(.pro)를 기사 끝에 삽입 (issue07_data.json · issue07_pro.json 실데이터)
  ④ 상단 등급 전환 버튼 + 등급 안내 띠
사용: python build_issue07_tiers.py → sellerkim_issue07_tiers.html
"""
import base64
import datetime as dt
import json
import re
from html import escape
from pathlib import Path

from build_issue07 import IMAGES
from issue07_free_rewrites import REWRITES

HERE = Path(__file__).parent
D = json.loads((HERE / "issue07_data.json").read_text())
PRO = json.loads((HERE / "issue07_pro.json").read_text())
IS, SEA = D["itemscout"], D["season"]

NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?\s*만(?:\s*\d[\d,]*\s*(?:천|백)?)?|\d[\d,]*\s*천|\d[\d,]*)(?=\s*(?:번|회|개))")


def mark_text(seg: str) -> str:
    return NUM.sub(lambda m: f'<span class="abs">{m.group(1)}</span>', seg)


def mark(body: str) -> str:
    body = re.sub(r'(<div class="v"><b>)([^<%]+)(</b>)', r'\1<span class="abs">\2</span>\3', body)   # %는 상대값이라 두기
    parts = re.split(r"(<[^>]+>)", body)
    return "".join(p if p.startswith("<") else mark_text(p) for p in parts)


def n(v):
    return f"{int(v):,}" if v is not None else "–"


def tbl(head, rows, right=()):
    th = "".join(f'<th class="{"r" if i in right else ""}">{h}</th>' for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td class="{"r" if i in right else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="pro-t"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def box(title, sub, inner, files):
    dl = "".join(f'<button type="button" disabled>{escape(f)}</button>' for f in files)
    return (f'<aside class="pro"><div class="pro-k">PRO 데이터</div><h4>{title}</h4><p class="pro-s">{sub}</p>{inner}'
            f'<div class="pro-dl">{dl}<span>미리보기 — 실제 서비스에서는 내려받기</span></div></aside>')


def is_rows(keys):
    return [[k, n(IS[k]["monthly"]), n(IS[k]["prd_cnt"]), f'{IS[k]["monthly"] / max(IS[k]["prd_cnt"], 1):.2f}'] for k in keys if k in IS]


def spark(shape):
    m = max(shape) or 1
    bars = "".join(f'<i style="height:{max(2, v / m * 18):.0f}px"></i>' for v in shape)
    return f'<span class="spk">{bars}</span>'


A = PRO["amazon"]
NAMES = {"us": "미국", "jp": "일본", "de": "독일", "uk": "영국"}
BOXES = {
    "cover": box("치이카와 연관 검색어 전체", "본문에 나온 네 검색어의 검색 대비 상품 비율. 1을 넘을수록 상품보다 찾는 사람이 많습니다.",
                 tbl(["검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["치이카와", "치이카와인어섬", "치이카와인형", "치이카와굿즈"]), {1, 2, 3}),
                 ["치이카와_연관어_52주.csv"]),
    "this-week": box(f"이번 주 위클리 키워드 {PRO['weekly_total']:,}개 중 상위 12", "본문은 상위 10개 이야기만 다룹니다. 프로에서는 전체 목록과 각 키워드의 3년 주간 추이를 받습니다.",
                     tbl(["순위", "키워드", "분류", "월 검색"], [[i + 1, k, c, n(s)] for i, (k, c, s) in enumerate(PRO["weekly_top"][:12])], {0, 3}),
                     [f"위클리키워드_2026-10-07_{PRO['weekly_total']}개.csv", "주간추이_3년.csv"]),
    "brand": box("어그 모델별 검색·상품", "브랜드 검색과 모델 검색을 나란히 놓으면 어디가 비어 있는지 보입니다.",
                 tbl(["검색어", "월 검색", "등록 상품", "검색÷상품"], is_rows(["어그", "어그슬리퍼", "어그타스만", "어그메리제인"]), {1, 2, 3}),
                 ["어그_모델별_52주.csv"]),
    "dispatch": box("네 나라 아마존 검색 상위 (10월 9일)",
                    "본문은 나라별 두세 개만 고릅니다. 프로에서는 " + " · ".join(f"{NAMES[c]} {A[c + '_n']:,}개" for c in NAMES) + " 키워드 전체를 받습니다.",
                    "".join(f"<h5>{NAMES[c]}</h5>" + tbl(["키워드", "카테고리", "검색 지표"], [[escape(k), escape(cat), n(s)] for k, cat, s, *_ in A[c][:5]], {2}) for c in NAMES),
                    ["아마존_4개국_2026-10-09.csv"]),
    "forecast": box(f"계절성 DB — 이번 호 후보 {len(SEA)}개 전체", "5년 주간 기록으로 계산한 정점 시기와 지금 위치. 막대는 1~12월 평균 모양입니다.",
                    tbl(["키워드", "월별 모양", "지금(정점 대비)", "정점", "배수", "월 검색", "등록 상품"],
                        [[k, spark(v["monthly_shape"]), f'{v["cur_pct"]}%', v["peak_date"], f'{v["lift"]}배', n(v.get("monthly")), n(v.get("prd_cnt"))]
                         for k, v in SEA.items()], {2, 4, 5, 6}),
                    ["계절성DB_5년_전체.csv"]),
}

CSS = """
.abs{transition:background .2s}
body[data-tier="free"] .v-p{display:none}
body:not([data-tier="free"]) .v-f{display:none}
body[data-tier="free"] .abs{color:transparent;background:var(--rule);border-radius:3px;letter-spacing:-.04em;position:relative;white-space:nowrap}
body[data-tier="free"] .abs::after{content:attr(data-m);position:absolute;inset:0;color:var(--muted);text-align:center;font-family:var(--mono);font-size:.82em;letter-spacing:0}
.pro{display:none;margin:26px 0;border:1.5px solid var(--ink);border-radius:6px;padding:16px 18px;background:var(--paper2);break-inside:avoid}
body[data-tier="pro"] .pro{display:block}
.pro-k{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;color:var(--hi);font-weight:600}
.pro h4{font-family:var(--serif);font-size:17px;margin:4px 0 4px}
.pro h5{font-size:12.5px;margin:12px 0 2px;color:var(--muted)}
.pro-s{font-size:13px;color:var(--muted);margin:0 0 8px;line-height:1.6}
.pro-t{overflow-x:auto}
.pro table{width:100%;border-collapse:collapse;font-size:12.5px}
.pro th{font-weight:500;color:var(--muted);text-align:left;border-bottom:1px solid var(--ink);padding:5px 6px;white-space:nowrap}
.pro td{border-bottom:1px solid var(--rule);padding:5px 6px}
.pro .r{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.pro-dl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;font-size:11.5px;color:var(--muted)}
.pro-dl button{font:600 12px var(--mono);padding:5px 10px;border:1px solid var(--ink);border-radius:4px;background:var(--paper);color:var(--ink);opacity:.75;cursor:not-allowed}
.spk{display:inline-flex;align-items:flex-end;gap:1px;height:18px}.spk i{display:block;width:4px;background:var(--brand);opacity:.8}
.tiers{position:fixed;left:14px;top:12px;z-index:7;display:flex;gap:4px;padding:4px;border:1px solid var(--rule);border-radius:999px;background:var(--paper);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.tiers button{font:600 12.5px var(--sans);border:0;background:none;color:var(--muted);padding:6px 12px;border-radius:999px;cursor:pointer}
.tiers button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.only-free,.only-plus{display:none}
body[data-tier="free"] .only-free,body[data-tier="plus"] .only-plus{display:flex}
body[data-tier="free"] span.only-free{display:inline}
.cta{align-items:center;gap:12px;flex-wrap:wrap;margin:22px 0 4px;padding:12px 14px;border:1px dashed var(--brand);border-radius:6px;break-inside:avoid}
.cta button{font:700 13.5px var(--sans);padding:8px 16px;border:0;border-radius:999px;background:var(--brand);color:#fff;cursor:pointer}
.cta.pro-up button{background:var(--ink);color:var(--paper)}
.cta span{font-size:12.5px;color:var(--muted)}
.cta-in{font:600 12.5px var(--sans);color:var(--brand);border:0;background:none;padding:0 0 0 6px;cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.gate{position:fixed;inset:0;z-index:20;display:none;align-items:center;justify-content:center;background:rgba(10,20,25,.45)}
.gate.on{display:flex}
.gate-box{width:min(340px,calc(100vw - 32px));background:var(--paper);color:var(--ink);border-radius:10px;padding:20px 20px 16px;box-shadow:0 10px 40px rgba(0,0,0,.25)}
.gate-box p{margin:0 0 4px;font:700 16px var(--sans)}.gate-box small{display:block;color:var(--muted);font-size:13px;margin-bottom:14px}
.gate-box div{display:flex;gap:8px;justify-content:flex-end}
.gate-box button{font:600 13.5px var(--sans);padding:8px 14px;border-radius:999px;border:1px solid var(--rule);background:none;color:var(--ink);cursor:pointer}
.gate-box button.go{background:var(--brand);border-color:var(--brand);color:#fff}
.ver{display:inline-block;font-family:var(--mono);font-size:11px;color:#fff;background:var(--hi);border-radius:3px;padding:1px 7px;margin-bottom:4px}
.tierband{margin:14px 0 4px;padding:10px 14px;border-radius:6px;font-size:13.5px;line-height:1.6;background:var(--paper2);border-left:3px solid var(--brand)}
.tierband>div{display:none}.tierband b{color:var(--ink)}
body[data-tier="free"] .tierband .t-free,body[data-tier="plus"] .tierband .t-plus,body[data-tier="pro"] .tierband .t-pro{display:block}
@media (max-width:520px){.tiers{top:auto;bottom:40px;left:50%;transform:translateX(-50%)}}
"""

BAND = """<div class="tierband">
<div class="t-free"><b>무료</b> · 0원 · 이메일 구독 — 이야기와 배수·증감률·순위는 그대로, 검색 횟수와 등록 상품 수는 몇 배·몇 %로만 보여 드립니다. 지난 호(과월호) 링크는 플러스부터 열립니다.</div>
<div class="t-plus"><b>플러스</b> · 월 9,900원 — 본문의 모든 정확한 수치와 지난 호 전체를 엽니다.</div>
<div class="t-pro"><b>프로</b> · 월 99,000~149,000원 — 플러스 전체에 더해, 기사마다 본문 밖의 원자료(전체 목록·시계열)를 표와 파일로 받습니다.</div>
</div>"""

JS = """<div class="tiers" role="group" aria-label="구독 등급 미리보기">
<button type="button" data-t="free">무료</button><button type="button" data-t="plus">플러스</button><button type="button" data-t="pro">프로</button></div>
<script>(()=>{
document.querySelectorAll('.abs').forEach(s=>s.setAttribute('data-m','██,███'));
const set=t=>{document.body.dataset.tier=t;document.querySelectorAll('.tiers button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.t===t));
  try{localStorage.setItem('sk-tier',t)}catch(e){};dispatchEvent(new Event('resize'));};
document.querySelectorAll('.tiers button').forEach(b=>b.addEventListener('click',()=>set(b.dataset.t)));
const gate=document.createElement('div');gate.className='gate';gate.setAttribute('role','dialog');gate.setAttribute('aria-modal','true');
gate.innerHTML='<div class="gate-box"><p></p><small></small><div><button type="button" class="go x">확인</button></div></div>';
document.body.appendChild(gate);
const MSG={plus:['플러스 이상 멤버만 볼 수 있습니다','검색수·상품수 숫자는 플러스 구독부터 보입니다.'],
  pro:['프로 멤버만 볼 수 있습니다','연관어 전체 데이터와 내려받기는 프로 구독에서 열립니다.'],
  back:['플러스 이상 멤버만 볼 수 있습니다','지난 호(과월호)는 플러스 구독부터 열립니다.']};
const warn=k=>{gate.querySelector('p').textContent=MSG[k][0];gate.querySelector('small').textContent=MSG[k][1];
  gate.classList.add('on');gate.querySelector('.x').focus();};
const close=()=>gate.classList.remove('on');
gate.addEventListener('click',e=>{if(e.target===gate||e.target.classList.contains('x'))close();});
addEventListener('keydown',e=>{if(e.key==='Escape')close();});
document.addEventListener('click',e=>{const a=e.target.closest('a.backissue, .issuenav a');
  if(a&&document.body.dataset.tier==='free'){e.preventDefault();warn('back');}},true);
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>warn(b.dataset.go)));
let t='free';try{t=localStorage.getItem('sk-tier')||'free'}catch(e){}
set(t);})();</script>"""


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


# 코너별 결제 유도 문구: (코너 끝 버튼, 문단 끝 링크) — 그 코너에서 숫자를 바꾼 키워드 이름 그대로
PLUS_CTA = {
    "cover": ("치이카와 검색수·상품수 확인", "치이카와 검색수 →"),
    "this-week": ("TOP 10 검색수 확인", "AI 서비스 검색수 →"),
    "brand": ("어그 검색수·상품수 확인", "어그 검색수 →"),
    "dispatch": ("약사의 혼잣말·대림절 달력 검색수 확인", "약사의 혼잣말 검색수 →"),
    "word": ("공덕키링 검색수·상품수 확인", "공덕키링 검색수 →"),
    "forecast": ("과메기·발열조끼·스키장 검색수 확인", "과메기 검색수 →"),
    "picks": ("눕시·핫팩·뚜레쥬르케이크 검색수 확인", "눕시 검색수 →"),
    "timing": ("여름운동화 상품수 확인", "여름운동화 상품수 →"),
    "followup": ("어드벤트캘린더·제미나이·메디큐브 검색수 확인", "어드벤트캘린더 상품수 →"),
    "watching": ("공덕키링 상품수 확인", "공덕키링 상품수 →"),
}
VERSION = "v1.0"   # 팀 공유본 버전. 미리보기를 고칠 때마다 올린다.

# 코너 제목 교체 (원문 → 새 제목)
TITLES = {"영화가 끌어올린 인형": "일본 아마존 1위 제품, 한국도 일주일 사이 검색량 두 배",
          "여름 신발 회사의 겨울": "여름 신발 회사가 겨울에 뜨는 이유",
          "네 나라에서 온 소식": "해외 트렌드 소식",
          "지금 사두면 좋은 것": "지금 사둬야 하는 것"}
PRO_CTA = {"cover": "치이카와 연관어 전체 데이터 보기", "this-week": f"위클리 키워드 {PRO['weekly_total']:,}개 전체 보기",
           "brand": "어그 모델별 데이터 보기", "dispatch": "아마존 4개국 키워드 전체 보기", "forecast": f"계절성 DB {len(SEA)}개 전체 보기"}


def add_cta(body: str) -> str:
    """무료: 숫자를 바꾼 첫 문단 끝 '정확한 숫자 →' + 코너 끝 '정확한 숫자 보기'. 플러스: 프로 상자 코너 끝 '관련 데이터 보기'."""
    out, pos = [], 0
    for m in re.finditer(r'<article id="([^"]+)"', body):
        out.append(body[pos:m.start()])
        end = body.index("</article>", m.start())
        art, aid = body[m.start():end], m.group(1)
        if 'class="v-f"' in art:
            pm = re.search(r'<p[^>]*>(?:(?!</p>).)*class="v-f"(?:(?!</p>).)*</p>', art, flags=re.S)
            if pm:
                para = pm.group(0)
                art = art.replace(para, para[:-4] + f'<span class="only-free"><button type="button" class="cta-in" data-go="plus">{PLUS_CTA[aid][1]}</button></span></p>', 1)
            art += (f'<div class="cta only-free"><button type="button" data-go="plus">{PLUS_CTA[aid][0]}</button>'
                    '<span>플러스 · 월 9,900원</span></div>')
        if m.group(1) in BOXES:
            art = art.replace('<aside class="pro">', f'<div class="cta pro-up only-plus"><button type="button" data-go="pro">{PRO_CTA[aid]}</button>'
                              '<span>프로 · 표와 파일 · 월 99,000원부터</span></div><aside class="pro">', 1)
        out.append(art)
        pos = end
    out.append(body[pos:])
    return "".join(out)


def main():
    html = (HERE / "issue07_template.html").read_text()
    a, b = html.index('<header class="mast">'), html.index("<footer>")
    head, body, tail = html[:a], mark(free_swap(html[a:b])), html[b:]
    left = len(re.findall(r'class="abs"', re.sub(r'<span class="v-p">.*?</span><span class="v-f">', '', body, flags=re.S)))
    print("무료판에서 바뀌지 않고 남은 수치:", left)
    for aid, bx in BOXES.items():
        i = body.index(f'<article id="{aid}"')
        j = body.index("</article>", i)
        body = body[:j] + bx + "\n" + body[j:]
    body = add_cta(body)
    for old, new in TITLES.items():
        body = body.replace(old, new)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = '<div class="meta">'
    assert body.count(meta) == 1
    body = body.replace(meta, f'<div class="meta"><span class="ver">등급 미리보기 {VERSION} · {stamp}</span><br>', 1)
    k = body.index("</header>") + len("</header>")
    body = body[:k] + "\n" + BAND + body[k:]
    head = head.replace("</style>", CSS + "</style>", 1).replace("<title>셀러KIM 10월 3주</title>", "<title>셀러KIM 7호 등급 미리보기</title>")
    html = head + body + tail + "\n" + JS
    for key, fname in IMAGES.items():
        f = HERE / "img" / fname
        if f.exists():
            html = html.replace("{{IMG_" + key + "}}", "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode())
    out = HERE / "sellerkim_issue07_tiers.html"
    out.write_text(html)
    print(f"{out.name} {out.stat().st_size / 1e6:.2f}MB · 가린 수치 {body.count('class=\"abs\"')}개 · 프로 상자 {len(BOXES)}개")


if __name__ == "__main__":
    main()
