"""셀러KIM 2호 HTML 빌드: 템플릿 + 차트 JS + 이미지(base64) + 데이터 → 단일 HTML.
아티팩트는 외부 이미지를 차단하므로 이미지는 data URI 로 내장한다."""
import base64
import json
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = {
    "COVER": ("un_fall_decor2.jpg", "Unsplash"),
    "DECOR1": ("un_fall_decor1.jpg", "Unsplash"),
    "LASH1": ("un_lash_salon.jpg", "Unsplash"),
    "LASH2": ("un_lash_tray.jpg", "Unsplash"),
    "WALKPAD": ("gen_walkingpad.jpg", "AI 생성(연출)"),
    "PATCH": ("gen_pimple_patch.jpg", "AI 생성(연출)"),
    "COAT": ("un_coat_rack.jpg", "Unsplash"),
    "SQUID": ("un_squid.jpg", "Unsplash"),
    "HW_KIDS": ("un_halloween_kids.jpg", "Unsplash"),
    "HW_TABLE": ("un_halloween_table.jpg", "Unsplash"),
    "KNIT": ("un_knit.jpg", "Unsplash"),
    "NV_PIZZA": ("nv_pizza_seolgi.jpg", "네이버쇼핑"),
    "NV_ACU": ("nv_acuster.jpg", "네이버쇼핑"),
    "NV_MAG": ("nv_magnesium_lactate.jpg", "네이버쇼핑"),
    "NV_CRAB": ("nv_crab.jpg", "네이버쇼핑"),
    "NV_IKSU": ("nv_iksu.jpg", "네이버쇼핑"),
    "NV_JACKET": ("nv_autumn_jacket.jpg", "네이버쇼핑"),
    "NV_WAK": ("nv_wakppuball.jpg", "네이버쇼핑"),
}
CREDITS = ("Unsplash 이미지는 Unsplash License(상업 이용 가능). "
           "네이버쇼핑 상품 이미지는 판매자 저작물로, 공개 발행 전 권리 확인이 필요합니다. "
           "워킹패드·여드름패치 장면 사진 2장은 Gemini 2.5 Flash Image 로 생성한 연출 이미지입니다(본문에 명시). "
           "사진은 주제를 대표하는 이미지이며 특정 상품의 공식 이미지가 아닙니다.")


def main() -> None:
    html = (HERE / "issue02_template.html").read_text()
    for key, (fname, _) in IMAGES.items():
        uri = "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / fname).read_bytes()).decode()
        html = html.replace("{{IMG_" + key + "}}", uri)
    html = html.replace("{{CREDITS}}", CREDITS)
    html = html.replace("{{DATA_JSON}}", json.dumps(
        json.loads((HERE / "issue02_data.json").read_text()), ensure_ascii=False, separators=(",", ":")))
    html = html.replace("{{CHART_JS}}", (HERE / "issue02_charts.js").read_text())

    out = HERE / "sellerkim_issue02.html"
    out.write_text(html)
    print(f"저장: {out.name} ({out.stat().st_size / 1e6:.2f} MB)")
    left = [k for k in ("{{IMG_", "{{DATA_JSON}}", "{{CHART_JS}}", "{{CREDITS}}") if k in html]
    print("[경고] 미치환:", left) if left else print("치환 완료")


if __name__ == "__main__":
    main()
