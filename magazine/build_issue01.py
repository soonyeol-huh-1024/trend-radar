"""
셀러킴 창간호 HTML 빌드: 템플릿 + 차트 JS + 이미지(base64) + 데이터 JSON → 단일 HTML.
아티팩트는 외부 이미지 로드를 차단하므로 이미지는 data URI 로 내장한다.

사용: python build_issue01.py   → magazine/sellerkim_issue01.html
"""
import base64
import json
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = {  # 템플릿 플레이스홀더 → 파일, 출처 (크레딧 섹션에 표기)
    "COVER": ("un_popmart_store.jpg", "Unsplash · Pop Mart 매장 진열"),
    "FIGURES": ("un_figures.jpg", "Unsplash · 컬러 피규어"),
    "RAMEN": ("un_ramen_bowl.jpg", "Unsplash · 라면 한 그릇"),
    "PLUSH": ("un_plush_wall.jpg", "Unsplash · 봉제인형 벽"),
    "EYELASH": ("un_eyelashes.jpg", "Unsplash · 속눈썹 클로즈업"),
    "HALLOWEEN": ("un_halloween_table.jpg", "Unsplash · 할로윈 테이블"),
    "HANBOK": ("un_hanbok.jpg", "Unsplash · 한복"),
    "STREETFOOD": ("un_korean_street_food.jpg", "Unsplash · 한국 길거리 음식"),
    "NV_PIZZA": ("nv_pizza_seolgi.jpg", "네이버쇼핑 상품 이미지 (아이템스카우트 API)"),
    "NV_GRAIN": ("nv_paradise_grain.jpg", "네이버쇼핑 상품 이미지 (아이템스카우트 API)"),
    "NV_MAG": ("nv_magnesium_lactate.jpg", "네이버쇼핑 상품 이미지 (아이템스카우트 API)"),
    "NV_ACU": ("nv_acuster.jpg", "네이버쇼핑 상품 이미지 (아이템스카우트 API)"),
}


def data_uri(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> None:
    html = (HERE / "issue01_template.html").read_text()
    js = (HERE / "issue01_charts.js").read_text()
    data = json.loads((HERE / "issue01_data.json").read_text())
    for key, (fname, _) in IMAGES.items():
        html = html.replace("{{IMG_" + key + "}}", data_uri(HERE / "img" / fname))
    credits = " · ".join(sorted({src for _, src in IMAGES.values()}))
    html = html.replace("{{CREDITS}}", credits)
    html = html.replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("{{CHART_JS}}", js)
    out = HERE / "sellerkim_issue01.html"
    out.write_text(html)
    print(f"저장: {out} ({out.stat().st_size / 1e6:.2f} MB)")
    left = [k for k in ("{{IMG_", "{{DATA_JSON}}", "{{CHART_JS}}", "{{CREDITS}}") if k in html]
    if left:
        print("[경고] 치환되지 않은 플레이스홀더:", left)


if __name__ == "__main__":
    main()
