"""셀러KIM 5호 HTML 빌드: 템플릿 + 이미지(base64) → 단일 HTML.
아티팩트는 외부 이미지를 차단하므로 이미지는 data URI 로 내장한다."""
import base64
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = {
    "COVER": "un5_shop_queue.jpg",
    "POKE30": "nv5_poke30b.jpg",
    "BINDER": "nv5_card_binder.jpg",
    "SLEEVES": "un5_card_sleeves.jpg",
    "BOTTLES": "un5_water_bottles.jpg",
    "LIGHTSTICK": "un5_lightsticks.jpg",
    "ALBUMS": "un5_albums.jpg",
    "TOKYO": "un5_tokyo_dome.jpg",
    "SYRUP": "un5_syrup.jpg",
    "BEERTENT": "un5_beer_tent.jpg",
    "FURCLOG": "un5_fur_clogs.jpg",
    "EXAMWATCH": "un5_exam_watch.jpg",
    "NAMI": "un5_nami_autumn.jpg",
    "ONSEN": "un_onsen.jpg",
    "GINGER": "nv5_ginger.jpg",
    "EPAD": "nv5_electric_pad.jpg",
    "KIMCHI": "un5_kimchi_fridge.jpg",
    "FOGGY": "un5_foggy_glasses.jpg",
    "SNOWBOOTS": "un5_snow_boots.jpg",
    "WINDOWAC": "un5_window_ac.jpg",
    "SUMMERBED": "un5_summer_bedding.jpg",
    "HANDFAN": "un5_handheld_fan.jpg",
    "CINEMA": "un_cinema.jpg",
    "PASTSEASON": "gen_past_season.jpg",
    "FOLLOWUP": "gen_followup.jpg",
    "WATCHING": "gen_watching.jpg",
}


def main() -> None:
    html = (HERE / "issue05_template.html").read_text()
    for key, fname in IMAGES.items():
        uri = "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / fname).read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)

    out = HERE / "sellerkim_issue05.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size / 1e6:.2f} MB)")
    left = [k for k in html.split("{{IMG_")[1:]]
    print("[경고] 미치환:", [x.split("}}")[0] for x in left]) if left else print("치환 완료")


if __name__ == "__main__":
    main()
