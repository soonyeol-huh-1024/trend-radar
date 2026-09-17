"""매거진 템플릿 → 이메일용 HTML 로 변환.

메일 클라이언트 제약 때문에 웹판을 그대로 못 쓴다:
  · Gmail 은 SVG 를 지운다        → 제호는 호스팅한 PNG 를 URL 로 건다
  · 본문 102KB 넘으면 잘라낸다     → 사진은 GitHub Pages 에 올린 것을 URL 로 부른다
  · <style> 블록과 CSS 변수를 지운다 → 색·간격을 전부 인라인 style 로 푼다
  · linear-gradient 지원이 고르지 않다 → 게이지·시점마크는 단색 테이블로 다시 그린다

사용: python build_email.py  →  out_email/body.html + 첨부 목록(manifest.json)
"""
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "out_email"
# 사진은 GitHub Pages 에 올린 것을 쓴다 — 첨부가 사라져 메일이 가벼워지고,
# 여러 호를 보내도 같은 파일을 다시 내려받지 않는다. (build_site.py 가 올린다)
SITE = "https://soonyeol-huh-1024.github.io/trend-radar"
INK, MUTED, RULE, PAPER2 = "#15242B", "#5B6B72", "#CFD8D5", "#E9EEEC"
BRAND, HI, GOOD = "#0E8AA6", "#C2452D", "#3A8F3F"
SANS = "'Apple SD Gothic Neo','Malgun Gothic',sans-serif"
MONO = "ui-monospace,Menlo,Consolas,monospace"
GAUGE_COLOR = {1: HI, 2: MUTED, 3: BRAND, 4: GOOD}
MARK_LABEL = {"m-past": "지나간 것", "m-now": "지금", "m-next": "올 것", "m-note": "풀이"}


def gauge(level: int) -> str:
    """네 칸 게이지 — 메일에서는 표로 그린다(빈 span 은 클라이언트가 접어버린다)."""
    cells = []
    for i in range(1, 5):
        c = GAUGE_COLOR[level] if i <= level else RULE
        cells.append(f'<td width="4" height="12" bgcolor="{c}" style="font-size:0">&nbsp;</td>'
                     f'<td width="2" style="font-size:0">&nbsp;</td>')
    return ('<table cellpadding="0" cellspacing="0" border="0" style="display:inline-table;'
            f'vertical-align:middle"><tr>{"".join(cells)}</tr></table>')


def mark(cls: str) -> str:
    """시점 마크 — 반쪽 채움은 메일에서 깨지므로 색과 라벨로 구분한다."""
    filled = cls in ("m-now", "m-past", "m-next")
    color = BRAND if filled else MUTED
    dot = (f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
           f'background:{color if cls == "m-now" else "transparent"};'
           f'border:2px solid {color};vertical-align:middle"></span>')
    return dot + f'<span style="color:{MUTED};font-size:10px;letter-spacing:.1em">&nbsp;{MARK_LABEL[cls]}</span>&nbsp;&nbsp;'



def _cover(m: re.Match) -> str:
    """표지 — 메일에서는 사진 위 글씨가 깨지므로 사진 아래로 내린다."""
    img, kicker, title, lede = m.group(1), m.group(2), m.group(3), m.group(4)
    return (f'<div style="margin:0 0 22px">'
            f'<img src="{img}" width="600" style="display:block;width:100%;max-width:600px;border-radius:3px;border:0" alt="">'
            f'<div style="background:{INK};color:#fff;padding:16px 18px;border-radius:0 0 3px 3px">'
            f'<div style="font-family:{MONO};font-size:10.5px;letter-spacing:.16em;opacity:.8;margin-bottom:5px">{kicker}</div>'
            f'<div style="font-size:22px;font-weight:700;line-height:1.3">{title}</div>'
            f'<div style="font-size:13.5px;line-height:1.6;opacity:.9;margin-top:7px">{lede}</div>'
            f'</div></div>')


def _toc(m: re.Match) -> str:
    rows = re.findall(r'<div class="k">(.*?)</div><div class="t">(.*?)</div>', m.group(1), re.S)
    out = []
    for k, t in rows:
        t = t.replace("<small>", f'<br><span style="color:{MUTED};font-size:12.5px;line-height:1.5">').replace("</small>", "</span>")
        out.append(f'<tr><td valign="top" width="72" style="font-family:{MONO};font-size:10.5px;letter-spacing:.1em;'
                   f'color:{MUTED};padding:5px 14px 5px 0;white-space:nowrap">{k}</td>'
                   f'<td valign="top" style="font-size:14px;padding:4px 0;line-height:1.55">{t}</td></tr>')
    return (f'<table cellpadding="0" cellspacing="0" border="0" width="100%" '
            f'style="margin:6px 0 4px;border-bottom:1px solid {RULE};padding-bottom:14px">{"".join(out)}</table>')


def _rank(m: re.Match) -> str:
    rows = re.findall(r'<div class="r"><div class="n">(.*?)</div><div class="b">(.*?)</div><div class="v">(.*?)</div></div>',
                      m.group(1), re.S)
    out = []
    for n, b, v in rows:
        b = re.sub(r'<b>(.*?)</b>', r'<div style="font-size:15.5px;font-weight:600;line-height:1.5">\1</div>', b, flags=re.S)
        b = re.sub(r'<span>(.*?)</span>', rf'<div style="font-size:13.5px;color:{MUTED};line-height:1.6;margin-top:2px">\1</div>', b, flags=re.S)
        v = re.sub(r'<b>(.*?)</b>', rf'<span style="color:{INK};font-size:14px;font-weight:600">\1</span> ', v, flags=re.S)
        out.append(f'<tr><td valign="top" width="32" style="font-family:{MONO};font-size:12.5px;color:{MUTED};'
                   f'padding:11px 10px 11px 0;border-top:1px solid {RULE}">{n}</td>'
                   f'<td valign="top" style="padding:11px 0;border-top:1px solid {RULE}">{b}'
                   f'<div style="font-family:{MONO};font-size:12px;color:{MUTED};margin-top:5px">{v}</div></td></tr>')
    return f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0">{"".join(out)}</table>'


def _fc(m: re.Match) -> str:
    cards = re.findall(r'<div><div class="w">(.*?)</div><b>(.*?)</b><span>(.*?)</span></div>', m.group(1), re.S)
    out = []
    for w, b, sp in cards:
        out.append(f'<tr><td style="background:{PAPER2};border-radius:3px;padding:13px 15px">'
                   f'<div style="font-family:{MONO};font-size:11px;letter-spacing:.08em;color:{BRAND};margin-bottom:4px">{w}</div>'
                   f'<div style="font-size:15.5px;font-weight:600;margin-bottom:2px">{b}</div>'
                   f'<div style="font-size:13.5px;color:{MUTED};line-height:1.6">{sp}</div></td></tr>'
                   f'<tr><td height="10" style="font-size:0;line-height:0">&nbsp;</td></tr>')
    return f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:20px 0">{"".join(out)}</table>'


def _legend(m: re.Match) -> str:
    items = re.findall(r'<div>(.*?)</div>\s*(?=<div>|$)', m.group(1), re.S)
    out = []
    for it in items:
        it = re.sub(r'<span>(.*?)</span>', r'\1', it, flags=re.S)
        out.append(f'<tr><td style="padding:5px 0;font-size:13.5px;color:{MUTED};line-height:1.7">{it}</td></tr>')
    return f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:12px 0">{"".join(out)}</table>'


def convert() -> tuple[str, list[dict]]:
    html = (HERE / "issue03_template.html").read_text()
    body = html.split("</style>", 1)[1]
    atts: list[dict] = []

    # 제호 SVG → 호스팅한 PNG
    body = re.sub(r'<h1 class="logo">.*?</h1>',
                  f'<img src="{SITE}/assets/logo.png" width="160" alt="셀러KIM" '
                  'style="display:block;border:0">', body, flags=re.S)

    # 게이지·시점마크
    body = re.sub(r'<span class="gap" data-l="(\d)"[^>]*>(?:<i></i>)+</span>',
                  lambda m: gauge(int(m.group(1))), body)
    body = re.sub(r'<span class="m (m-\w+)"[^>]*></span>', lambda m: mark(m.group(1)), body)

    # 사진 → 호스팅 URL. 첨부가 없어 메일이 가볍고 전문을 다 실을 수 있다.
    from build_issue03 import IMAGES
    for key in dict.fromkeys(re.findall(r'\{\{IMG_(\w+)\}\}', body)):
        body = body.replace("{{IMG_" + key + "}}", f"{SITE}/assets/img/{IMAGES[key]}")

    # 구조물은 표로 다시 짠다 — div 나열은 메일에서 무너진다
    body = re.sub(r'<div class="cover">\s*<img src="(cid:\w+)"[^>]*>\s*<div class="line">\s*'
                  r'<div class="k">(.*?)</div>\s*<h2>(.*?)</h2>\s*<p>(.*?)</p>\s*</div>\s*</div>',
                  _cover, body, flags=re.S)
    body = re.sub(r'<div class="toc">(.*?)</div>\s*\n\s*<div class="note">', lambda m: _toc(m) + '<div class="note">', body, flags=re.S)
    body = re.sub(r'<div class="rank">(.*?)\n  </div>', _rank, body, flags=re.S)
    body = re.sub(r'<div class="fc">(.*?)\n  </div>', _fc, body, flags=re.S)
    body = re.sub(r'<div class="legend">(.*?)\n  </div>', _legend, body, flags=re.S)

    # 클래스 → 인라인 스타일
    S = {
        "cover": f'margin:0 0 20px', "toc": f'padding:18px 0;border-bottom:1px solid {RULE}',
        "note": f'padding:20px 0;border-bottom:1px solid {RULE};font-size:15px;line-height:1.85',
        "kicker": f'font-family:{MONO};font-size:11px;letter-spacing:.12em;color:{MUTED};margin:0 0 8px',
        "deck": f'font-size:16px;line-height:1.7;color:{MUTED};margin:0 0 18px',
        "sub": f'font-size:18px;font-weight:700;margin:26px 0 8px;color:{INK};line-height:1.45',
        "pull": f'font-size:19px;line-height:1.55;font-weight:500;margin:24px 0;padding:4px 0 4px 16px;border-left:3px solid {BRAND};color:{INK}',
        "memo": f'border-left:3px solid {RULE};padding:2px 0 2px 14px;margin:22px 0;font-size:14px;color:{MUTED};line-height:1.75',
        "box": f'background:{PAPER2};border-radius:3px;padding:18px 20px 8px;margin:24px 0',
        "row": f'padding:14px 0;border-top:1px solid {RULE}',
        "lede": f'font-size:14px;color:{MUTED};margin:0 0 6px',
        "legend": "margin:16px 0",
    }
    for cls, style in S.items():
        body = re.sub(rf'class="{cls}"', f'style="{style}"', body)
        body = re.sub(rf'class="(\w+) {cls}"', f'style="{style}"', body)

    body = body.replace('<article class="short">', '<div style="padding:30px 0;border-bottom:1px solid ' + RULE + '">')
    body = body.replace("<article>", '<div style="padding:34px 0;border-bottom:1px solid ' + RULE + '">')
    body = body.replace("</article>", "</div>")
    body = re.sub(r'<h2>', f'<h2 style="font-size:24px;line-height:1.3;margin:0 0 10px;color:{INK};font-weight:700">', body)
    body = re.sub(r'<h3 style=', '<h3 style=', body)
    body = re.sub(r'<h4>', f'<h4 style="font-size:16px;font-weight:600;margin:0 0 2px;color:{INK}">', body)
    # 영상은 메일에서 재생할 수 없으므로 유튜브로 보내는 검은 판으로 바꾼다
    def _vid(m):
        yt, title, by, cap = m.group(1), m.group(2), m.group(3), m.group(4).strip()
        url = f"https://www.youtube.com/watch?v={yt}"
        return (f'<div style="margin:22px 0">'
                f'<a href="{url}" style="text-decoration:none;color:#fff">'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'
                f' style="background:#12161a;border-radius:3px"><tr>'
                f'<td align="center" style="padding:44px 24px;color:#fff;font-family:inherit">'
                f'<div style="font-size:30px;line-height:1;color:#fff">&#9654;</div>'
                f'<div style="font-size:15px;font-weight:600;color:#fff;margin-top:14px">{title}</div>'
                f'<div style="font-size:11.5px;color:rgba(255,255,255,.6);margin-top:5px;'
                f'font-family:ui-monospace,Menlo,monospace">{by}</div>'
                f'</td></tr></table></a>'
                f'<div style="font-size:12.5px;color:{MUTED};margin-top:6px;line-height:1.6">{cap} '
                f'<a href="{url}" style="color:{MUTED}">유튜브에서 보기 &#8599;</a></div></div>')
    body = re.sub(r'<figure class="vid[^"]*" data-yt="([\w-]+)">.*?<b>(.*?)</b>'
                  r'<span class="by">(.*?)</span>.*?<figcaption>(.*?)\s*<a [^>]*>.*?</a>'
                  r'\s*</figcaption>\s*</figure>', _vid, body, flags=re.S)
    body = re.sub(r'<figure[^>]*>', '<div style="margin:20px 0">', body)
    body = body.replace("</figure>", "</div>")
    body = re.sub(r'<figcaption>', f'<div style="font-size:12.5px;color:{MUTED};margin-top:6px;line-height:1.6">', body)
    body = body.replace("</figcaption>", "</div>")
    # 원격 이미지를 막는 클라이언트가 있으므로 alt 를 남긴다
    body = re.sub(r'<img src="(' + re.escape(SITE) + r'/assets/img/[^"]+)"[^>]*alt="([^"]*)"[^>]*>',
                  r'<img src="\1" width="600" alt="\2" style="display:block;width:100%;max-width:600px;border-radius:3px;border:0">', body)
    body = re.sub(r'<img src="(' + re.escape(SITE) + r'/assets/img/[^"]+)"(?![^>]*alt=)[^>]*>',
                  r'<img src="\1" width="600" alt="" style="display:block;width:100%;max-width:600px;border-radius:3px;border:0">', body)
    body = re.sub(r'<span class="mono[^"]*">', '<span style="font-family:monospace">', body)
    body = re.sub(r'<span class="hl r">', f'<span style="background:#FAE3DC;padding:0 3px">', body)
    body = re.sub(r'<span class="hl">', f'<span style="background:#FFF0B8;padding:0 3px">', body)
    body = re.sub(r'<b class="hl r">', f'<b style="background:#FAE3DC;padding:0 3px">', body)
    body = re.sub(r'<b class="hl">', f'<b style="background:#FFF0B8;padding:0 3px">', body)
    body = re.sub(r'<div class="(rank|fc|gapx|v|n|b|r|k|t|w|m)"', '<div', body)
    body = re.sub(r'class="[\w\- ]*"', "", body)                      # 남은 클래스 제거
    body = re.sub(r'<p>', '<p style="margin:0 0 15px;font-size:15px;line-height:1.85">', body)
    body = body.replace("</div>\n</div>", "</div></div>")

    body = re.sub(r'\n\s*\n+', '\n', body)
    body = re.sub(r'\n\s+<', '\n<', body)
    head = (f'<div style="max-width:600px;margin:0 auto;padding:24px 18px 50px;'
            f'background:#F4F6F5;font-family:{SANS};color:{INK};-webkit-text-size-adjust:100%">')
    return head + body.replace("<div >", "<div>") + "</div>", atts


def main() -> None:
    OUT.mkdir(exist_ok=True)
    html, atts = convert()
    (OUT / "body.html").write_text(html)
    for a in atts:
        a["b64"] = base64.b64encode(Path(a["path"]).read_bytes()).decode()
    (OUT / "manifest.json").write_text(json.dumps(
        [{k: v for k, v in a.items() if k != "b64"} for a in atts], ensure_ascii=False, indent=1))
    (OUT / "attachments.json").write_text(json.dumps(atts, ensure_ascii=False))
    kb = len(html.encode()) / 1024
    total = sum(len(base64.b64decode(a["b64"])) for a in atts) / 1e6
    print(f"본문 {kb:.0f}KB (Gmail 잘림 기준 102KB) · 첨부 {len(atts)}개 {total:.2f}MB")


if __name__ == "__main__":
    main()
