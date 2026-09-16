"""
후보 키워드를 워커 큐(Firestore keyword_list)에 READY 로 등록 → 워커가 tt/gg/az 분석 → BQ trend_daily.
이후 fetch_series.py / hit_score.py 로 시그니처(az_pre·틱톡 스파이크·구글 급등)를 수치로 검증한다.

사용: python register_candidates.py "chiikawa:US" "chiikawa:JP" "inositol:US" ...
      (이미 같은 keyword+lang 이 READY/ANALYZE 상태면 건너뜀)
"""
import sys
from datetime import datetime, timezone

from google.cloud import firestore

DB = firestore.Client(project="gen-lang-client-0493835715", database="trend-checker")
PLATFORMS = ["TikTok", "Google Trends", "Amazon"]


def main() -> None:
    specs = [a for a in sys.argv[1:] if ":" in a]
    if not specs:
        sys.exit("사용: register_candidates.py keyword:LANG ...")
    now = datetime.now(timezone.utc)
    col = DB.collection("keyword_list")
    for spec in specs:
        kw, lang = spec.rsplit(":", 1)
        kw, lang = kw.strip(), lang.strip().upper()
        dup = [d for d in col.where("keyword", "==", kw).where("lang_code", "==", lang).stream()
               if d.to_dict().get("status") in ("READY", "ANALYZE")]
        if dup:
            print(f"  건너뜀 (이미 {dup[0].to_dict()['status']}): {kw} [{lang}]")
            continue
        ref = col.document()
        ref.set({
            "keyword": kw, "lang_code": lang, "platforms": PLATFORMS, "status": "READY",
            "date": now.strftime("%y%m%d"), "source": "trend_radar",
            "createdAt": now, "updatedAt": now,
        })
        print(f"  등록: {kw} [{lang}] → {ref.id}")


if __name__ == "__main__":
    main()
