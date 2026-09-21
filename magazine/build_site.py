"""매거진 템플릿 → GitHub Pages 정적 사이트(docs/).

아티팩트판은 이미지를 base64 로 박아 2.4MB 가 되지만, 호스팅하면 이미지를
파일로 두고 URL 로 참조하면 되므로 HTML 이 50KB 로 줄고 브라우저가 캐시한다.
메일에서도 같은 URL 을 쓸 수 있어 CID 첨부가 필요 없어진다.

공개 호스팅이라 네이버쇼핑 상품 이미지(판매자 저작물)를 쓰는 호는 올리지 않는다.

사용: python build_site.py   →  ../docs/
"""
import re
import shutil
from pathlib import Path

HERE = Path(__file__).parent
DOCS = HERE.parent / "docs"
BASE = "/trend-radar"                       # GitHub Pages 하위 경로

# 공개 가능한 호만. (1·2호는 img/nv_*.jpg 를 써서 제외 — 판매자 저작물)
ISSUES = [
    {"n": 4, "slug": "issue-04", "tpl": "issue04_template.html", "mod": "build_issue04",
     "title": "아이 옷이 먼저 바뀝니다", "date": "2026년 9월 5주",
     "lede": "계절이 바뀔 때 옷장은 한꺼번에 바뀌지 않습니다. 순서가 있고, 그 순서의 맨 앞은 어른이 아니었습니다.",
     "cover": "gen_kid_windbreaker.jpg"},
    {"n": 3, "slug": "issue-03", "tpl": "issue03_template.html", "mod": "build_issue03",
     "title": "영화가 끝나고 한 달 반 뒤", "date": "2026년 9월 4주",
     "lede": "8월 5일에 개봉한 영화의 원작 책이 지금 팔리기 시작했습니다. 늦게 오는 수요에는 나름의 시간표가 있습니다.",
     "cover": "un_cinema.jpg"},
]

DOC = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
{og_image}<link rel="icon" href="{base}/assets/favicon.svg">
</head>
<body>
{body}
</body>
</html>
"""


def build_issue(it: dict, assets: set[str]) -> None:
    mod = __import__(it["mod"])
    html = (HERE / it["tpl"]).read_text()
    for key, fname in mod.IMAGES.items():
        html = html.replace("{{IMG_" + key + "}}", f"{BASE}/assets/img/{fname}")
        assets.add(fname)
    html = re.sub(r"<title>.*?</title>\s*", "", html, count=1)
    # 폰트 링크는 head 로 올린다
    links = re.findall(r'<link rel="[^"]*"[^>]*>', html)
    html = re.sub(r'<link rel="[^"]*"[^>]*>\s*', "", html)

    out = DOCS / it["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(DOC.format(
        title=f'셀러KIM 제{it["n"]}호 — {it["title"]}',
        desc=it["lede"], base=BASE,
        og_image=f'<meta property="og:image" content="{BASE}/assets/img/{it["cover"]}">\n',
        body="\n".join(links) + "\n" + html))
    kb = (out / "index.html").stat().st_size / 1024
    print(f"  {it['slug']}/index.html  {kb:.0f}KB")


def _logo() -> str:
    """제호 SVG 본문. 파일 맨 앞 주석만 떼낸다(SVG 안에도 주석이 있어 마지막 -->로 자르면 안 된다)."""
    raw = (HERE / "brand/logo_sellerkim.svg").read_text()
    return re.sub(r"^\s*<!--.*?-->\s*", "", raw, count=1, flags=re.S).strip()


def build_index(assets: set[str]) -> None:
    cards = "\n".join(
        f'''  <a class="card" href="{BASE}/{it["slug"]}/">
    <img src="{BASE}/assets/img/{it["cover"]}" alt="">
    <div class="t">
      <div class="k">제{it["n"]}호 · {it["date"]}</div>
      <h2>{it["title"]}</h2>
      <p>{it["lede"]}</p>
    </div>
  </a>''' for it in ISSUES)
    for it in ISSUES:
        assets.add(it["cover"])

    (DOCS / "index.html").write_text(DOC.format(
        title="셀러KIM — 주간 트렌드 매거진", base=BASE,
        desc="검색 데이터에서 아직 자리가 비어 있는 것을 찾아 매주 정리합니다.",
        og_image=f'<meta property="og:image" content="{BASE}/assets/img/{ISSUES[0]["cover"]}">\n',
        body=f'''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@500;700&family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
:root{{--paper:#F4F6F5;--paper2:#E9EEEC;--ink:#15242B;--muted:#5B6B72;--rule:#CFD8D5;--brand:#0E8AA6;
 --sans:'IBM Plex Sans KR','Apple SD Gothic Neo',sans-serif;--mono:'IBM Plex Mono',monospace;--serif:'Hahmlet',serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--paper:#101A1F;--paper2:#18242A;--ink:#E6ECEA;--muted:#9AABB0;--rule:#2A3A41;--brand:#1F98B8}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.8;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:680px;margin:0 auto;padding:44px 22px 70px}}
.mast{{padding-bottom:14px;border-bottom:2px solid var(--ink);margin-bottom:10px}}
.mast svg{{width:196px;height:auto;color:var(--ink);display:block}}
.stand{{font-size:16.5px;color:var(--muted);margin:16px 0 34px;line-height:1.75;max-width:52ch}}
.card{{display:grid;grid-template-columns:200px 1fr;gap:20px;text-decoration:none;color:inherit;
  padding:22px 0;border-top:1px solid var(--rule)}}
.card img{{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:3px;filter:saturate(.88)}}
.card .k{{font-family:var(--mono);font-size:11px;letter-spacing:.12em;color:var(--muted);margin-bottom:6px}}
.card h2{{font-family:var(--serif);font-size:21px;margin:0 0 7px;font-weight:700;line-height:1.35}}
.card p{{margin:0;font-size:14.5px;color:var(--muted);line-height:1.65}}
.card:hover h2{{color:var(--brand)}}
@media (max-width:540px){{.card{{grid-template-columns:1fr;gap:12px}}}}
footer{{margin-top:44px;padding-top:22px;border-top:1px solid var(--rule);font-size:13px;color:var(--muted);line-height:1.75}}
a{{color:var(--brand)}}
:focus-visible{{outline:2px solid var(--brand);outline-offset:3px}}
</style>
<div class="wrap">
<header class="mast">{_logo()}</header>
<p class="stand">검색 데이터에서 <b>아직 자리가 비어 있는 것</b>을 찾아 매주 정리합니다.<br>
셀러와 트렌드를 보는 사람 모두를 위한 읽을거리입니다.</p>
{cards}
<footer>
<p>제1·2호는 상품 이미지 권리 확인이 끝나면 올립니다.</p>
<p>코드 · 데이터 파이프라인 <a href="https://github.com/soonyeol-huh-1024/trend-radar">github.com/soonyeol-huh-1024/trend-radar</a></p>
</footer>
</div>'''))
    print(f"  index.html  {(DOCS / 'index.html').stat().st_size / 1024:.0f}KB")


def main() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    (DOCS / "assets/img").mkdir(parents=True)
    (DOCS / ".nojekyll").touch()          # Jekyll 처리 비활성화

    assets: set[str] = set()
    print("빌드:")
    for it in ISSUES:
        build_issue(it, assets)
    build_index(assets)

    total = 0
    for f in sorted(assets):
        src = HERE / "img" / f
        if src.exists():
            shutil.copy2(src, DOCS / "assets/img" / f)
            total += src.stat().st_size
    shutil.copy2(HERE / "brand/logo_sellerkim.svg", DOCS / "assets/favicon.svg")
    # 메일 클라이언트는 SVG 를 지우므로 PNG 제호도 같이 올린다 (build_email.py 가 참조)
    shutil.copy2(HERE / "brand/logo_email.png", DOCS / "assets/logo.png")
    print(f"  assets/img  {len(assets)}장 {total/1e6:.1f}MB")


if __name__ == "__main__":
    main()
