"""셀러KIM 6호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML.
아티팩트는 외부 이미지를 차단하므로 이미지는 data URI 로 내장한다."""
import base64
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = {
    "COVER": "un6_advent_cover.jpg",
    "ADVENTOPEN": "un6_advent_open.jpg",
    "SQUISHY": "nv6_squishy.jpg",
    "EBLANKET": "un6_electric_blanket.jpg",
    "MEDICUBE": "nv6_medicube.jpg",
    "HALLOWEEN": "un6_halloween_costume.jpg",
    "TOKYO": "un6_tokyo_cinema.jpg",
    
    "WREATH": "un6_advent_wreath.jpg",
    "LONGPUFFER": "un6_long_puffer.jpg",
    "SHEEPSKIN": "un6_sheepskin_boots.jpg",
    "PARTY": "un6_party_room.jpg",
    "VEST": "un6_puffer_vest.jpg",
    "LEGO": "un6_lego_bricks.jpg",
    "CAKE": "un6_strawberry_cake.jpg",
    "SAFETY": "un6_safety_boots.jpg",
    "WORKVEST": "un6_work_vest.jpg",
    "SLIME": "un6_slime.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
}


def main() -> None:
    html = (HERE / "issue06_template.html").read_text()
    for key, fname in IMAGES.items():
        f = HERE / "img" / fname
        if not f.exists():
            print("[경고] 이미지 없음:", fname)
            continue
        uri = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)

    out = HERE / "sellerkim_issue06.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size / 1e6:.2f} MB)")
    left = [k for k in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", [x.split("}}")[0] for x in left]) if left else print("치환 완료")


if __name__ == "__main__":
    main()
