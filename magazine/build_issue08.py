"""셀러KIM 8호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML."""
import base64
from pathlib import Path
HERE = Path(__file__).parent
IMAGES = {
    "COVER": "gen8_tonerpads.jpg",
    "PUFFER": "un8_puffer_window.jpg",
    "RUNNING": "un8_running_street.jpg",
    "LEGO": "un6_lego_bricks.jpg",
    "POPCORN": "un8_popcorn.jpg",
    "XMASTREE": "un8_xmas_tree.jpg",
    "AUTUMN": "un8_autumn_wall.jpg",
    "SKI": "un8_ski.jpg",
    "PLANNER": "un8_planner.jpg",
    "COOLPAD": "nv8_coolpad.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
}
def main():
    html = (HERE / "issue08_template.html").read_text()
    for key, fname in IMAGES.items():
        f = HERE / "img" / fname
        if not f.exists():
            print("[경고] 이미지 없음:", fname); continue
        uri = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)
    out = HERE / "sellerkim_issue08.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size/1e6:.2f} MB)")
    left = [x.split("}}")[0] for x in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", left) if left else print("치환 완료")
if __name__ == "__main__":
    main()
