"""셀러KIM 3호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML.
아티팩트는 외부 이미지를 차단하므로 이미지는 data URI 로 내장한다."""
import base64
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = {
    "PASTSEASON": "gen_past_season.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
    "CHIIKAWA": "nv_chiikawa.jpg",
    "CINEMA": "un_cinema.jpg",
    "BOOKSHELF": "un_bookshelf.jpg",
    "PLUSH": "un_plush_shelf.jpg",
    "PROTEIN": "un_protein.jpg",
    "STRESS": "un_stress.jpg",
    "TRAIL": "un_autumn_trail.jpg",
    "ROASTERY": "un_roastery.jpg",
    "PAMPAS": "un_pampas.jpg",
    "BIRCH": "un_birch.jpg",
    "ONSEN": "un_onsen.jpg",
    "SITPLUSH": "gen_sitting_plush.jpg",
    "COFFEESACK": "un_coffee_sack.jpg",
}


def main() -> None:
    html = (HERE / "issue03_template.html").read_text()
    for key, fname in IMAGES.items():
        uri = "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / fname).read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)

    out = HERE / "sellerkim_issue03.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size / 1e6:.2f} MB)")
    left = [k for k in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", [x.split("}}")[0] for x in left]) if left else print("치환 완료")


if __name__ == "__main__":
    main()
