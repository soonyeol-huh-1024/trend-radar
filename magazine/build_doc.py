"""셀러KIM 원고 추출: 템플릿 → 문장 다듬기용 문서(HTML/DOCX).

지면 장치(단 나눔·게이지·기호)는 빼고 읽고 고칠 말만 남긴다.
굵게·형광펜은 그대로 살려서 어디를 강조했는지 보이게 한다.
사진·영상 자리는 [사진]/[영상]으로 표시만 하고 캡션은 고칠 수 있게 둔다.
"""
import re, subprocess, sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

HERE = Path(__file__).parent
ISSUE = "제3호"
DATE = "2026년 9월 4주"

GRAY = "color:#777"
NOTE = f'style="{GRAY};font-size:10.5pt"'          # 고칠 말이 아닌 표시


def ink(node) -> str:
    """문단 속 서식만 남긴다 — 굵게, 형광펜, 고정폭."""
    if node is None:
        return ""
    out = []
    for c in node.children:
        if isinstance(c, NavigableString):
            out.append(str(c))
            continue
        cls = c.get("class", [])
        inner = ink(c)
        if c.name in ("b", "strong"):
            out.append(f"<b>{inner}</b>")
        elif "hl" in cls:
            # 형광펜은 밑줄로 남긴다 — 워드로 옮길 때 바탕색은 사라지고 밑줄만 남는다
            if "r" in cls:
                out.append(f'<span style="color:#c0392b">'
                           f'<u style="background:#ffd9d4">{inner}</u></span>')
            else:
                out.append(f'<u style="background:#fff3a3">{inner}</u>')
        elif c.name == "a":
            out.append(inner)
        elif c.name == "br":
            out.append(" ")
        elif "m" in cls and any(x.startswith("m-") for x in cls):
            pass                                    # 시점 마크 — 글이 아니다
        elif "gap" in cls or "gapx" in cls:
            pass                                    # 빈자리 게이지
        else:
            out.append(inner)
    return re.sub(r"[ \t]+", " ", "".join(out)).strip()


def p(html, tag="p", extra=""):
    return f"<{tag} {extra}>{html}</{tag}>" if html else ""


def block(el) -> list[str]:
    cls = el.get("class", [])
    out = []
    if el.name == "h2":
        out.append(p(ink(el), "h2"))
    elif el.name == "h3":
        out.append(p(ink(el), "h3"))
    elif el.name == "p":
        if "kicker" in cls:
            out.append(p("▸ " + ink(el), "p", NOTE))
        elif "pull" in cls:
            out.append(p("“" + ink(el) + "”", "p", 'style="margin-left:24px;font-style:italic"'))
        else:
            out.append(p(ink(el)))
    elif el.name == "figure":
        if "vid" in cls:
            b = el.select_one(".play b"); by = el.select_one(".play .by")
            out.append(p(f"[영상] {ink(b)} — {ink(by)}", "p", NOTE))
        else:
            img = el.find("img")
            out.append(p(f"[사진] {img.get('alt', '') if img else ''}", "p", NOTE))
        label = "영상설명" if "vid" in cls else "사진설명"
        for cap in el.select("figcaption"):
            for a in cap.select("a"):
                a.extract()                         # '유튜브에서 보기' 는 지면 장치다
            out.append(p(f"{label} · " + ink(cap)))
    elif "pair" in cls:
        for f in el.select("figure"):
            out.extend(block(f))
    elif "rank" in cls:
        for i, r in enumerate(el.select(".r"), 1):
            n = ink(r.select_one(".n")) or str(i)
            name = ink(r.select_one(".b b"))
            desc = ink(r.select_one(".b span"))
            v = r.select_one(".v")
            num = ink(v.find("b")) if v and v.find("b") else ""
            rest = ink(v)[len(num):].strip() if v else ""
            rest = re.sub(r"(포화|빡빡|여유|넉넉)$", r"· \1", rest).strip()
            side = f' <span style="{GRAY}">({num} {rest})</span>' if num else ""
            out.append(p(f"<b>{n} {name}</b>{side}" + (f"<br>{desc}" if desc else "")))
    elif "fc" in cls:
        for d in el.find_all("div", recursive=False):
            spans = d.find_all("span")
            w = ink(d.select_one(".w"))
            name = ink(d.find("b"))
            desc = ink(spans[-1]) if spans else ""
            out.append(p(f'<span style="{GRAY}">{w}</span> <b>{name}</b>'
                         + (f"<br>{desc}" if desc and desc != w else "")))
    elif "row" in cls:                             # 기사에 바로 놓인 항목(팔로업 등)
        h4 = el.find("h4"); n = el.select_one(".n")
        head = f"<b>{ink(h4)}</b>" if h4 else ""
        if n:
            head += f'<br><span style="{GRAY}">{ink(n)}</span>'
        out.append(p(head))
        for q in el.find_all("p", recursive=False):
            out.append(p(ink(q)))
    elif "box" in cls:
        k = el.select_one(".k"); h3 = el.find("h3")
        if k: out.append(p("▸ " + ink(k), "p", NOTE))
        if h3: out.append(p(ink(h3), "h3"))
        for row in el.select(".row"):
            h4 = row.find("h4"); n = row.select_one(".n")
            head = f"<b>{ink(h4)}</b>" if h4 else ""
            if n: head += f'<br><span style="{GRAY}">{ink(n)}</span>'
            out.append(p(head))
            for q in row.find_all("p", recursive=False):
                out.append(p(ink(q)))
    elif "memo" in cls:
        out.append(p(ink(el), "p", 'style="margin-left:24px"'))
    elif "legend" in cls:
        pass                                        # 기호 범례 — 글이 아니다
    return [x for x in out if x]


def main() -> None:
    soup = BeautifulSoup((HERE / "issue03_template.html").read_text(), "html.parser")
    pages = soup.select_one(".pages")
    doc = [
        f"<h1>셀러KIM {ISSUE}</h1>",
        p(f"{DATE} · 문장 다듬기용 원고", "p", NOTE),
        p("고치실 곳은 본문 문장입니다. ▸ 로 시작하는 줄과 [사진]·[영상] 표시는 "
          "어디에 무엇이 들어가는지 알려 주는 것이니 그대로 두셔도 됩니다. "
          "<u>밑줄</u>은 지면에서 형광펜으로 나가고, "
          '<span style="color:#c0392b"><u>빨간 밑줄</u></span>은 빨간 형광펜입니다. '
          "굵은 글씨도 그대로 굵게 나갑니다.", "p", NOTE),
        "<hr>",
    ]
    cover = pages.select_one(".cover .line")
    if cover:
        doc.append("<h2>표지</h2>")
        doc.append(p("▸ " + ink(cover.select_one(".k")), "p", NOTE))
        doc.append(p(ink(cover.find("h2")), "h3"))
        doc.append(p(ink(cover.find("p"))))

    toc = pages.select_one(".toc")
    if toc:
        doc.append("<h2>목차</h2>")
        ks = toc.select(".k"); ts = toc.select(".t")
        for k, t in zip(ks, ts):
            small = t.find("small")
            sub = ink(small) if small else ""
            if small: small.extract()
            doc.append(p(f'<span style="{GRAY}">{ink(k)}</span> <b>{ink(t)}</b>'
                         + (f'<br><span style="{GRAY}">{sub}</span>' if sub else "")))

    note = pages.select_one(".note")
    if note:
        doc.append("<h2>편집자의 말</h2>")
        for q in note.find_all("p"):
            doc.append(p(ink(q)))

    for i, art in enumerate(pages.select("article"), 1):
        h2 = art.find("h2")
        doc.append(p(f"{i}. {ink(h2) if h2 else ''}", "h2"))
        for el in art.find_all(recursive=False):
            if el is h2:
                continue
            doc.extend(block(el))

    foot = pages.find("footer")
    if foot:
        doc.append("<h2>발행 안내</h2>")
        for q in foot.find_all(["p", "div"], recursive=False):
            t = ink(q)
            if t:
                doc.append(p(t))

    html = ("<!doctype html><html><head><meta charset='utf-8'><title>셀러KIM " + ISSUE +
            "</title><style>body{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;"
            "font-size:11pt;line-height:1.7;max-width:820px;margin:40px auto}"
            "h1{font-size:22pt}h2{font-size:15pt;margin-top:32px;border-bottom:1px solid #ddd;padding-bottom:4px}"
            "h3{font-size:12.5pt;margin-top:20px}p{margin:0 0 10px}</style></head><body>"
            + "\n".join(doc) + "</body></html>")

    out = HERE / "out_doc"
    out.mkdir(exist_ok=True)
    (out / "sellerkim_issue03_원고.html").write_text(html)
    subprocess.run(["textutil", "-convert", "docx", "-output",
                    str(out / "셀러KIM_3호_원고.docx"), str(out / "sellerkim_issue03_원고.html")], check=True)
    words = len(re.sub(r"<[^>]+>", "", html).split())
    print(f"저장: out_doc/셀러KIM_3호_원고.docx · 단락 {html.count('<p')}개 · 낱말 {words}개")


if __name__ == "__main__":
    main()
