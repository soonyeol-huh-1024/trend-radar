"""셀러KIM 9호 등급판 프로 상자 데이터: 위클리 키워드(10/26) 상위 · 아마존 4개국 검색 상위(10/23) · 난방용품 순위 → issue09_pro.json"""
import ast, json, re
from pathlib import Path
from google.cloud import firestore

HERE = Path(__file__).parent
DROP = {"이준석", "xxx-videos", "xxx-video"}   # 인명·성인 검색어는 본문 순위처럼 뺀다
HEAT = re.compile(r"hot water bottle|electric blanket|heated blanket|heater|heizlüfter|wärmflasche|heizdecke|heizung|湯たんぽ|電気毛布|ヒーター|こたつ|heating pad|hand warmer", re.I)


def main():
    db = firestore.Client(project="gen-lang-client-0493835715", database="trend-checker")
    meta = db.collection("weekly_keywords").document("2026-10-26").get().to_dict()
    kws = []
    for i in range(int(meta["chunks"])):
        kws += db.collection("weekly_keywords").document(f"2026-10-26_chunk_{i}").get().to_dict()["keywords"]
    kws = sorted((k for k in kws if k["keyword"] not in DROP), key=lambda k: -(k.get("searchCnt") or 0))
    out = {"weekly_total": int(meta["totalKeywords"]),
           "weekly_top": [[k["keyword"], k["category"].split(" > ")[0], k["searchCnt"]] for k in kws[:20]], "amazon": {}}
    for c in ("us", "uk", "de", "jp"):
        d = db.collection("amazon_weekly").document(f"{c}_2026-10-23").get().to_dict()
        sr = d["searchRanking"]; sr = ast.literal_eval(sr) if isinstance(sr, str) else sr
        out["amazon"][c] = [[r["keyword"], r.get("category") or "", r["search_cnt"]] for r in [r for r in sr if r["keyword"] not in DROP][:10]]
        out["amazon"][c + "_n"] = len(sr)
        out["amazon"][c + "_heat"] = [[i + 1, r["keyword"], r["search_cnt"]] for i, r in enumerate(sr) if HEAT.search(r["keyword"])]
    (HERE / "issue09_pro.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["weekly_total"], out["weekly_top"][:3], {c: out["amazon"][c + "_heat"] for c in ("us", "uk", "de", "jp")})


if __name__ == "__main__":
    main()
