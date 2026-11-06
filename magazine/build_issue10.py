"""셀러KIM 10호 HTML 빌드: 9호 템플릿 머리·꼬리 + 10호 본문 + 해외 커뮤니티 기사 + 이미지(base64) → 단일 HTML."""
import base64
from pathlib import Path
HERE = Path(__file__).parent
IMAGES = {
    "COVER": "un10_radio_sill.jpg",
    "RADIO": "az10_amz_radio1.jpg",
    "UKRESERVOIR": "cm10_uk_reservoir.jpg",
    "UKPUMPKIN": "cm10_uk_pumpkin.jpg",
    "CN1111": "cm10_cn_1111.jpg",
    "AUSHALLOWEEN": "cm10_aus_halloween.jpg",
    "NZHALLOWEEN": "cm10_nz_halloween.jpg",
    "AUSUNSCREEN": "cm10_au_sunscreen.jpg",
    "COSTCOGAME": "cm10_us_costco_game.jpg",
    "MXCATRINA": "cm10_mx_catrina.jpg",
    "MYCLEARSKY": "cm10_my_clearsky.jpg",
    "SGSUNRISE": "cm10_sg_sunrise.jpg",
    "GIMBBQ": "cm10_us_gim_bbq.jpg",
    "GIMBUGAK": "cm10_us_gim_bugak.jpg",
    "GIMEXPIRE": "cm10_us_gim_expire.jpg",
    "LIGHTPUFFER": "gen_light_puffer.jpg",
    "HALLOWEEN": "un6_halloween_costume.jpg",
    "PEACH": "nv10_seolah_peach.jpg",
    "XMASTREE": "un8_xmas_tree.jpg",
    "GWAMEGI": "nv7_gwamegi.jpg",
    "BOOTS": "un5_snow_boots.jpg",
    "GOTGAM": "un10_gotgam1.jpg",
    "SANDALS": "un10_sandals.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
}
TOC = '해외 커뮤니티 일주일 <small>나라별로 본 11.11 쿠폰, 비상키트, 할로윈, 그리고 김</small>'


def main():
    t9 = (HERE / "issue09_template.html").read_text()
    b9 = (HERE / "issue09_body.html").read_text()
    i = t9.index(b9[:200]); j = t9.index(b9[-200:]) + 200
    head, tail = t9[:i], t9[j:]
    head = head.replace("제9호 · 2026년 10월 5주", "제10호 · 2026년 11월 1주")
    assert "제10호" in head
    body = (HERE / "issue10_body.html").read_text()
    body = body.replace("{{COMMUNITY_ARTICLE}}", (HERE / "issue10_community.html").read_text()).replace("{{COMMUNITY_TOC}}", TOC)
    tpl = head + body + tail
    import re
    tpl = re.sub(r"<title>[^<]*</title>", "<title>셀러KIM 제10호 · 11월 1주</title>", tpl, count=1)
    (HERE / "issue10_template.html").write_text(tpl)
    html = tpl
    for key, fname in IMAGES.items():
        f = HERE / "img" / fname
        if not f.exists():
            print("[경고] 이미지 없음:", fname); continue
        html = html.replace("{{IMG_" + key + "}}", "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode())
    out = HERE / "sellerkim_issue10.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size/1e6:.2f} MB)")
    left = [x.split("}}")[0] for x in html.split("{{")[1:]]
    print("[경고] 미치환:", left) if left else print("치환 완료")


if __name__ == "__main__":
    main()
