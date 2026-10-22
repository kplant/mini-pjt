# 공식 제출 스펙

교육 측이 준 제출 규약 원문이다(2026-10-22 사용자 제공). 이 프로젝트에서 정한 해석은 아래 "이 프로젝트의 적용"에 적는다.

## API 스펙
```
POST /query
Content-Type: application/json
Body: {"question": "사용자 질의"}

Response:
{
  "answer": "근거 기반 응답",
  "contexts": [{"doc_id": "...", "text": "..."}, ...],
  "trace": [{"step": "retrieve", "input": "...", "output": "..."}, ...]
}
```

## 산출물 구조
```
mini-pjt_{본인이름}/
├── src/                       # 소스코드
│   ├── agent.py               # 메인 에이전트 그래프
│   ├── tools.py               # 도메인 도구
│   ├── retriever.py           # RAG 파이프라인
│   └── ...
├── data/                      # 사용한 문서·데이터
├── evaluation/
│   ├── test_queries.csv       # 인-아웃 세트 (§4-4 스키마 필수 · 자체 평가·최종 채점의 기준)
│   ├── round1_report.md       # 1차 자체 평가 결과 (Day 9)
│   └── round2_report.md       # 2차 자체 평가 결과 (Day 10 · 개선 후)
├── SERVICE.md                 # 서비스 스펙 (§4-3 템플릿 필수)
├── Dockerfile                 # 클린 환경 재현 (선택사항)
├── requirements.txt
├── README.md                  # §4-5 템플릿 준수
└── run.sh                     # 실행 스크립트 (선택)
```

## 이 프로젝트의 적용
- 요청 본문은 `question`이 필수이고, `user_id`(기본 `sec-kim`), `thread_id`, `base_date`(기본 오늘)는 선택이다(`src/app.py`).
- `trace`는 route → 도구 호출 → `decision` 단계 순서다. 평가 판정 값은 마지막 `decision` 단계에 담는다.
- 폴더 이름 `mini-pjt_김상열`로 바꾸는 일은 TASKS 6-2에서 한다.
- Dockerfile과 run.sh는 선택이지만 둘 다 만든다(TASKS 6-3, 6-4).
- 스펙에 없는 파일(CLAUDE.md, CONTEXT.md, TASKS.md, docs/, plan/)도 그대로 둔다.
- §4-3(SERVICE.md 템플릿), §4-4(test_queries.csv 스키마), §4-5(README 템플릿) 원문은 아직 이 파일에 없다.
