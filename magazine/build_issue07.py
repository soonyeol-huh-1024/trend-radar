"""셀러KIM 7호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML."""
import base64
from pathlib import Path
HERE = Path(__file__).parent
IMAGES = {
    "COVER": "un7_cinema_crowd.jpg",
    "CINEMA": "un6_tokyo_cinema.jpg",
    "KNIT": "un7_knitwear.jpg",
    "UGG": "un6_sheepskin_boots.jpg",
    "HALLOWEEN": "un6_halloween_costume.jpg",
    "ADVENT": "un6_advent_open.jpg",
    "GONGDEOK": "nv7_gongdeok.jpg",
    "GWAMEGI": "nv7_gwamegi.jpg",
    "SKI": "un7_ski_resort.jpg",
    "DOWNJACKET": "un7_down_jacket.jpg",
    "HANDWARMER": "nv7_handwarmer.jpg",
    "LEGO": "un6_lego_bricks.jpg",
    "CAKE": "un6_strawberry_cake.jpg",
    "DESKFAN": "un7_desk_fan.jpg",
    "SUMMERSHOES": "un7_summer_sneakers.jpg",
    "SUMMERSHIRTS": "un7_summer_shirts.jpg",
    "PASTSEASON": "gen_past_season.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
}
def main():
    html = (HERE / "issue07_template.html").read_text()
    for key, fname in IMAGES.items():
        f = HERE / "img" / fname
        if not f.exists():
            print("[경고] 이미지 없음:", fname); continue
        uri = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)
    out = HERE / "sellerkim_issue07.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size/1e6:.2f} MB)")
    left = [x.split("}}")[0] for x in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", left) if left else print("치환 완료")
if __name__ == "__main__":
    main()
