"""셀러KIM 4호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML.
아티팩트는 외부 이미지를 차단하므로 이미지는 data URI 로 내장한다."""
import base64
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = {
    "COATRACK": "un_coat_rack.jpg",
    "KIDWIND": "gen_kid_windbreaker.jpg",
    "KNIT": "un_knit.jpg",
    "PHONE": "un_phone_box.jpg",
    "DESIGNDESK": "gen_design_desk.jpg",
    "PLUSHSHELF": "un_plush_shelf.jpg",
    "FALLDECOR1": "un_fall_decor1.jpg",
    "FALLDECOR2": "un_fall_decor2.jpg",
    "HALLOWEENKIDS": "un_halloween_kids.jpg",
    "GUASHA": "gen_guasha.jpg",
    "FORESTWALK": "un_forest_walk.jpg",
}


def main() -> None:
    html = (HERE / "issue04_template.html").read_text()
    for key, fname in IMAGES.items():
        uri = "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / fname).read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)

    out = HERE / "sellerkim_issue04.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size / 1e6:.2f} MB)")
    left = [k for k in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", [x.split("}}")[0] for x in left]) if left else print("치환 완료")


if __name__ == "__main__":
    main()
