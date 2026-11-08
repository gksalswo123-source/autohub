# 🤖 AutoHub

[![tests](https://github.com/gksalswo123-source/autohub/actions/workflows/tests.yml/badge.svg)](https://github.com/gksalswo123-source/autohub/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![cost](https://img.shields.io/badge/AI%20%EC%B4%88%EC%95%88-%EB%AC%B4%EB%A3%8C-orange)

> 공모전 찾기부터 기획서 초안까지, 대학생의 반복 작업을 터미널 한 줄로 자동화합니다.
>
> *A CLI for Korean university students: collect contests, sync deadlines to Todoist/calendar, and draft proposals with free AI.*

**이런 분께 좋아요:** 공모전 사이트를 매일 들어가기 귀찮은 분 · 마감일을 자꾸 놓치는 분 · 기획서 첫 줄이 안 써지는 분

```bash
auto contests --keyword AI --days 14
```

```
                    공모전 5건  (새로 올라온 것 2건)
┌──────┬──────────┬──────────────────────────────────────┬──────────────┐
│ 마감 │ 상태     │ 공모전                               │ 주최         │
├──────┼──────────┼──────────────────────────────────────┼──────────────┤
│  D-2 │ 마감임박 │ 2026 DATA·AI 분석 경진대회           │ 한국과학기술… │
│  D-7 │ 마감임박 │ NEW 생성형 AI 캐릭터 공모전           │ ○○시         │
└──────┴──────────┴──────────────────────────────────────┴──────────────┘
```

## ✨ 기능

| 상태 | 기능 | 명령어 |
|---|---|---|
| ✅ | 공모전·대회 공고 수집, 마감일순 정렬 | `auto contests` |
| ✅ | 키워드 / 분야 / 마감일 필터 | `-k AI -c 기획 -d 7` |
| ✅ | 새로 올라온 공고 표시 (NEW) | 자동 |
| ✅ | CSV(엑셀) / JSON / Markdown 저장 | `--save csv` |
| ✅ | 골라서 Todoist 할 일로 등록 (중복 방지, 마감 임박 순 우선순위) | `--todoist` |
| ✅ | 캘린더 파일(.ics) 내보내기, 마감 3일 전 알림 | `--save ics` |
| ✅ | 사이트에 없는 학과·교내 행사 직접 추가 | `auto add` |
| ✅ | **무료** AI 아이디어·기획서·발표 초안 (요강 자동 반영, API 키 불필요) | `auto draft` |
| 🚧 | 매일 아침 자동 실행 + 알림 | 4단계 |

전체 계획은 [ROADMAP.md](ROADMAP.md)를 보세요.

## 🚀 설치 (처음 해보는 분도 OK)

1. [Python 3.10 이상](https://www.python.org/downloads/)을 설치합니다. 설치 화면에서 **"Add Python to PATH"** 를 꼭 체크하세요.
2. 이 저장소를 내려받고 폴더로 이동합니다.
   ```bash
   git clone https://github.com/gksalswo123-source/autohub.git
   cd autohub
   ```
3. 설치합니다.
   ```bash
   pip install -e .
   ```
4. 실행해 봅니다.
   ```bash
   auto contests
   ```

## 📖 사용법

```bash
auto contests                       # 최신 공모전 2페이지(약 30건)
auto contests -p 5                  # 5페이지까지 읽기
auto contests -k AI                 # 제목·주최사에 "AI"가 들어간 것
auto contests -c 기획 --open        # 기획/아이디어 분야, 지금 접수 중인 것만
auto contests -d 7 --save csv       # 마감 7일 이내, 엑셀로 열 수 있는 CSV로 저장
auto --help                         # 전체 도움말
```

저장된 파일은 `output/` 폴더에 생깁니다.

### 📅 Todoist · 캘린더 연동

1. Todoist 웹 → **설정 → 연동 서비스 → 개발자** 에서 API 토큰을 복사합니다.
2. 토큰을 복사한 상태에서 `auto setup` 을 실행합니다. 붙여넣을 필요 없이 클립보드에서 읽고, 맞는지 바로 확인한 뒤
   홈 폴더의 `.autohub/.env` 에 저장하므로, 이후엔 어느 폴더에서 실행해도 됩니다.
   (직접 관리하고 싶다면 `.env.example` 을 `.env` 로 복사해 써도 됩니다.)
3. 실행합니다.
   ```bash
   auto contests -k AI --open --todoist     # 표를 보고 번호(예: 1,3,5-7)를 골라 추가
   auto contests -d 7 --todoist --yes       # 마감 7일 이내 전부 추가 (자동 실행용)
   auto contests --todoist --project 대회    # 다른 프로젝트에 추가
   ```
   - "공모전" 프로젝트가 없으면 자동으로 만들고, 마감일·링크·주최사가 함께 들어갑니다.
   - 이미 넣은 공모전은 다시 넣지 않습니다 (`~/.autohub/data/todoist_added.json` 에 기록).

사이트에 없는 학과·교내 행사는 직접 넣을 수 있습니다.

```bash
auto add "무역학부 PT 대회" --date 12/1 --organizer "영남대 무역학부" --url "공지 링크"
```

### ✍️ 무료 AI 초안 (API 키·결제 필요 없음)

공모 요강을 자동으로 읽어 **AI에게 보낼 맞춤 질문문**을 만들고, 클립보드에 복사한 뒤 claude.ai 창을 엽니다.
`Ctrl+V` → Enter 만 하면 초안이 나옵니다.

```bash
auto contests -k AI --draft                       # 목록에서 번호 하나 골라 아이디어 5개
auto contests --draft --kind 기획서                # 기획서 초안
auto draft --url "위비티 상세 주소" -k 발표          # 5분 발표 대본 + 예상 질문
auto draft "무역학부 PT 대회" -k 기획서 -m "무역학부 3학년 2명, 엑셀 분석 가능"
```

- 종류(`--kind`): `아이디어`(기본), `기획서`, `발표`
- `--memo` 에 팀 정보(전공, 인원, 할 수 있는 것)를 넣으면 더 현실적인 결과가 나옵니다.
- 질문문은 `output/drafts/` 에 저장되며, AI 답변을 그 파일에 붙여 보관할 수 있습니다.
- AI가 수치를 지어내지 않도록 `[확인 필요]` 표시를 하게 했습니다. 제출 전 꼭 확인하세요.

Google 캘린더·아웃룩을 쓴다면 `auto contests --save ics` 로 만든 파일을 가져오기(Import)하세요.

## 🧩 구조

```
src/autohub/
├── cli.py            # 'auto' 명령어 (입구)
├── models.py         # 공모전 한 건의 데이터 모양
├── storage.py        # 파일 저장(csv/json/md/ics) + NEW 판별 기록
├── todoist.py        # Todoist 할 일 등록
├── drafts.py         # 무료 AI 초안 질문문 만들기
├── config.py         # .env 에서 토큰 읽기
└── sources/          # 사이트별 수집기 (플러그인처럼 추가 가능)
    ├── base.py
    └── wevity.py
```

## 🤝 기여하기

새 공모전 사이트 수집기를 추가하고 싶다면 `sources/` 에 파일 하나를 만들고 `sources/__init__.py` 에 등록하면 됩니다. 이슈와 PR 모두 환영합니다!

```bash
pip install -e ".[dev]"
pytest
```

## ⚠️ 주의

- 각 사이트의 이용약관과 robots.txt를 지키며, 페이지 사이에 쉬는 시간을 두어 서버에 부담을 주지 않습니다.
- 수집한 정보의 저작권은 각 사이트와 주최사에 있습니다. 정확한 마감일·요강은 반드시 원문에서 확인하세요.

## 📄 라이선스

MIT
