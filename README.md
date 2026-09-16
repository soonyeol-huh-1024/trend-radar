# trend-radar

주간 트렌드 매거진 **셀러킴**과, 그 기사를 떠받치는 키워드 분석 파이프라인.

오픈마켓·SNS 검색 데이터에서 "아직 자리가 비어 있는 키워드"를 찾아
매주 열 개 코너로 정리하고, 그중 일부를 기사로 풀어 발행한다.

---

## 무엇을 푸는가

성장률만 보면 매주 같은 것이 상위에 온다. 10월이면 패딩이다.
`여성패딩`은 3년 평균 16.5배로 오르지만 등록 상품이 **388만 개**다.
누구나 아는 정보이고, 그래서 이미 다 들어가 있다.

그래서 모든 코너가 **한 달 검색 ÷ 등록 상품 수**를 함께 본다.
이 비율이 클수록 찾는 사람에 비해 파는 사람이 적다.

| 비율 | 뜻 |
|---|---|
| 100 이상 | 넉넉 |
| 20~100 | 여유 |
| 3~20 | 빡빡 |
| 3 미만 | 포화 |

같은 주에 `치이카와`는 검색 17.5만에 상품 165,132개(포화)이고,
`치이카와 앉은누이`는 6,450번에 **48개**(넉넉)다. 큰 문은 닫혀 있고 옆문은 비어 있다.

---

## 코너 열 개

| | 코너 | 소스 | 모듈 |
|---|---|---|---|
| ① | This Week 10 | 네이버 주간 키워드 | `radar/naver_corners.py` |
| ② | Emerging | 〃 (8주 전 대비 최근 4주) | 〃 |
| ③ | Cross-border | Amazon US/JP/DE + ItemScout | `radar/bridge_corners.py` |
| ④ | Seasonal Radar | 주간 시계열 최대 471주 | `radar/seasonal.py` |
| ⑤ | TikTok → Search | Exolyt 해시태그 + 네이버 | `radar/bridge_corners.py` |
| ⑥ | Search → Commerce | 네이버 주간 키워드 | `radar/naver_corners.py` |
| ⑦ | Falling Trends | 〃 (피크 대비 현재) | 〃 |
| ⑧⑨⑩ | Deep Dive · Seller Ideas · Watchlist | 앞 일곱 코너 결과 | 사람이 고른다 |

⑧⑨⑩ 은 스크립트가 고르지 않는다. `out/brief.json` 에 후보를 모아두고
무엇을 깊게 팔지는 사람이 판단한다.

### Seasonal Radar

최대 9년치 주간 검색 기록에서 **지금이 아니라 2~8주 뒤에 오르는** 키워드만 고른다.
같은 달력 주차끼리 묶어 연도 평균을 내고, 직전 8주가 이미 더 높았으면 계절이 지난 것으로 보고 버린다.

결과는 두 갈래로 나뉜다. 티켓·입장권류는 등록 상품이 적은 게
자리가 비어서가 아니라 **애초에 네이버쇼핑에서 파는 물건이 아니기 때문**이라,
상품 후보와 섞으면 오해를 부른다.

---

## 실행

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python fetch_candidates.py 30      # Firestore → data/cand_*.csv
python fetch_amazon_bq.py          # BigQuery  → data/cand_amazon_bq.csv

python run_radar.py                # 열 코너 후보 → out/
python run_radar.py --skip seasonal
```

```bash
cd magazine
python build_issue03.py            # 템플릿 + 사진(base64) → 단일 HTML
python build_email.py              # 메일 클라이언트용 변환
```

`data/`, `out/`, 빌드된 HTML 은 커밋하지 않는다. 위 명령으로 다시 만들어진다.

---

## 매거진

`magazine/GUIDE.md` 에 편집 기준이 있다. 요지만 옮기면,

- 독자는 셀러·트렌드 리더·일반 관심자 셋이다. **모든 코너가 셀러를 겨냥할 필요는 없다.**
- 데이터를 나열하지 않는다. 코너는 목록이 아니라 **기사**다 — 제목·부제·리드·맺음이 있다.
- 차트는 한 호에 한 개. 사진은 실사만 쓰고 톤을 맞춘다. **내용과 맞는 사진이 없으면 넣지 않는다.**
- 내부 계산 용어를 독자에게 내보내지 않는다.

### 기호

본문에 두 가지 기호를 쓴다.

- **빈자리 게이지** 네 칸 — 위의 검색÷상품 비율
- **시점 마크** — 코너가 어느 시간을 다루는지(지나간 것 / 지금 / 올 것 / 풀이).
  코너 배경색도 같은 체계를 따른다.

제호(`magazine/brand/logo_sellerkim.svg`)는 자모를 기하 도형으로 그린 레터링이고,
'킴'의 ㅣ 가 빈자리 게이지 네 칸과 같은 형태다.

---

## 자격증명

이 저장소에는 비밀정보가 없다. 스크립트가 실행 시점에 바깥에서 읽는다.

| 무엇 | 어디서 |
|---|---|
| ItemScout 쿠키 | `../worker/src/naver.ts` |
| Gemini API 키 | `../worker/.env` |
| Firestore · BigQuery | Application Default Credentials (`gcloud auth login`) |

---

## 이미지

- `magazine/img/un_*.jpg` — Unsplash License, 상업 이용 가능
- `magazine/img/gen_*.jpg` — 직접 생성. 매거진 꼬리말에 생성 이미지임을 밝힌다
- `magazine/img/nv_*.jpg` — **네이버쇼핑 상품 이미지(판매자 저작물). 커밋하지 않는다.**
  2호 빌드에 필요하면 ItemScout API 로 다시 받는다
