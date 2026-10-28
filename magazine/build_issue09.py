"""셀러KIM 9호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML."""
import base64
from pathlib import Path
HERE = Path(__file__).parent
IMAGES = {
    "COVER": "un9_cover_hwb.jpg",
    "HEATER": "un9_heater.jpg",
    "HEATMAT": "nv_heat_mat.jpg",
    "PLUSH": "un9_plush.jpg",
    "HALLOWEEN": "un6_halloween_costume.jpg",
    "OSMANTHUS": "un9_osmanthus.jpg",
    "LONGPUFFER": "un6_long_puffer.jpg",
    "ONSEN": "un_onsen.jpg",
    "CRAB": "un9_crab_market.jpg",
    "SWIMRING": "un9_swimring.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
}
def main():
    html = (HERE / "issue09_template.html").read_text()
    for key, fname in IMAGES.items():
        f = HERE / "img" / fname
        if not f.exists():
            print("[경고] 이미지 없음:", fname); continue
        uri = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)
    out = HERE / "sellerkim_issue09.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size/1e6:.2f} MB)")
    left = [x.split("}}")[0] for x in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", left) if left else print("치환 완료")
if __name__ == "__main__":
    main()
