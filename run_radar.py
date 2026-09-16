"""셀러킴 주간 레이더 — 10개 코너 후보를 한 번에 뽑는다.

사용: python run_radar.py [--skip seasonal]
출력: out/c01~c07_*.csv + out/brief.json (⑧⑨⑩ 큐레이션용 요약)

⑧ One Deep Dive · ⑨ Seller Ideas · ⑩ Next Week Watchlist 는 스크립트가 고르지 않는다.
앞의 일곱 코너 결과를 brief.json 에 모아두고, 무엇을 깊게 팔지는 세션에서 판단한다.
"""
import sys
from datetime import date

from radar import bridge_corners as bc
from radar import naver_corners as nc
from radar import seasonal as sr
from radar.common import dump_json, load_naver, weeks_of, write

SKIP = set(sys.argv[sys.argv.index("--skip") + 1].split(",")) if "--skip" in sys.argv else set()


def main() -> None:
    brief: dict = {"generated": date.today().isoformat(), "corners": {}}
    rows = load_naver()
    print(f"네이버 주간 키워드 {len(rows):,}행 / 최신 {weeks_of(rows)[-1]}\n")

    print("① This Week 10")
    c1 = nc.this_week_10(rows)
    write("c01_this_week.csv", c1, nc.COLS + ["wow", "score"])
    brief["corners"]["this_week"] = [
        {k: r.get(k) for k in ("keyword", "cat_top", "monthly", "prd_cnt", "ratio", "wow")} for r in c1]

    print("② Emerging")
    c2 = nc.emerging(rows)
    write("c02_emerging.csv", c2, nc.COLS + ["base", "recent", "lift"])
    brief["corners"]["emerging"] = [
        {k: r.get(k) for k in ("keyword", "cat_top", "monthly", "prd_cnt", "ratio", "lift")} for r in c2]

    print("③ Cross-border")
    c3 = bc.cross_border()
    write("c03_crossborder.csv", c3, ["az_kw", "az_country", "az_search", "ko", "monthly", "prd_cnt", "gap"])
    brief["corners"]["crossborder"] = c3

    if "seasonal" not in SKIP:
        print("④ Seasonal Radar")
        prod, exp = sr.radar()
        write("c04_seasonal_product.csv", prod, sr.COLS)
        write("c04_seasonal_outing.csv", exp, sr.COLS)
        brief["corners"]["seasonal_product"] = [
            {k: r.get(k) for k in ("keyword", "lift", "peak_week", "monthly", "prd_cnt", "ratio")} for r in prod]
        brief["corners"]["seasonal_outing"] = [
            {k: r.get(k) for k in ("keyword", "lift", "peak_week", "monthly")} for r in exp]

    print("⑤ TikTok→Search")
    c5 = bc.tiktok_to_search()
    write("c05_tiktok_search.csv", c5,
          ["hashtag", "cc", "views_total", "growth4w", "category", "ko", "monthly", "prd_cnt", "ratio"])
    brief["corners"]["tiktok_search"] = c5

    print("⑥ Search→Commerce")
    c6 = nc.search_to_commerce(rows)
    write("c06_search_commerce.csv", c6, nc.COLS + ["lift8"])
    brief["corners"]["search_commerce"] = [
        {k: r.get(k) for k in ("keyword", "cat_top", "monthly", "prd_cnt", "ratio", "lift8")} for r in c6]

    print("⑦ Falling Trends")
    c7 = nc.falling(rows)
    write("c07_falling.csv", c7, nc.COLS + ["peak", "vs_peak", "weeks_since_peak"])
    brief["corners"]["falling"] = [
        {k: r.get(k) for k in ("keyword", "cat_top", "monthly", "peak", "vs_peak", "weeks_since_peak")} for r in c7]

    dump_json("brief.json", brief)
    print("\n⑧⑨⑩ (Deep Dive · Seller Ideas · Watchlist) 은 brief.json 을 보고 세션에서 작성")


if __name__ == "__main__":
    main()
