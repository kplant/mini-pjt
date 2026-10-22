# 계획: TASKS 3-4 일정 Agent 프로필 조회·외부 인물 등록·소개 자료 검색

## Context
- 확인 항목: m-13, m-14, m-20, m-22~m-24 통과, m-22의 `contexts`에 `doc_id="ext_park_abc.md"`
  - m-13 박정우 대표 연락처 → 010-1234-5678, park@abc.example
  - m-14 임수빈 이사(XYZ사) 프로필 등록 → DB에 프로필 생성
  - m-20 DEF사 최동혁 대표(없는 사람) → no_answer=true
  - m-22 박정우 대표는 어떤 분? → "반도체 장비", ext_park_abc.md
  - m-23 고은비 교수 연구 분야 → "배터리"
  - m-24 GHI사 최근 소식(자료 없음) → no_answer=true
- 도구는 이미 있음: `get_profile`·`register_external_profile`(src/tools.py), `build_search_tool`·`search_intro`(src/retriever.py, 대상 자료가 없으면 검색 없이 no_answer)
- 남은 일: 일정 Agent 연결, 검색 결과를 contexts에 문서별로, 검색 trace 단계 이름 `retrieve`(docs/submission-spec.md 42행), 라우팅 확장

## 변경 파일 (2026-10-22 사용자 승인)
1. `src/agent.py`
   - `SCHEDULE_TOOL_NAMES`에 tool_get_profile, tool_register_external_profile. `build_schedule_agent`는 `retriever.build_search_tool(_intro_store())`의 tool_search_intro를 더함
   - `_intro_store()`: Chroma를 처음 쓸 때 한 번 열어 재사용
   - `SCHEDULE_PROMPT`: 연락처·직책·소속 → tool_get_profile, 어떤 분·경력·회사 소개·연구 분야·최근 소식 → tool_search_intro(답은 검색 내용만), 외부 인물 등록은 요청 값 그대로, no_answer·not_found면 reason 전달
   - `build_contexts`: tool_search_intro 결과는 조각마다 {doc_id: source, text: content}, 다른 도구는 지금 형식 유지
   - `build_trace`: tool_search_intro 단계 이름을 `retrieve`로
   - `SUPERVISOR_PROMPT`·일정 Agent 설명: 프로필·연락처, 외부 인물 등록, 소개 자료 질문 → schedule_agent
2. `README.md`: 구현 범위 3-4까지, RAG 설명에 retrieve 단계와 contexts doc_id 한 줄
3. `TASKS.md` 3-4 `[x]`, 이 파일 끝에 결과. tools.py·retriever.py는 바꾸지 않음

## 검증
1. m-13·m-14·m-20·m-22·m-23·m-24 각 3회(reset_db): route=일정, refused=false, must_include, no_answer(m-20·m-24), m-14 DB의 people 행, m-22·m-23 contexts doc_id = expected_source와 retrieve 단계, m-24 retrieve output no_answer
2. 회귀 각 1회: m-01~m-03·m-08~m-12(route=일정 + DB), m-04~m-07·m-21(route=조율), check_tools.py 36개
3. 커밋 `TASKS 3-4: 일정 Agent 프로필·외부 인물·소개 자료`

## 위험
- m-22에서 프로필만 조회하면 "반도체 장비"와 contexts가 빠짐 → 흔들리면 프롬프트 보강, 결과에 기록
- m-13 연락처는 trace·contexts에 그대로 남음(마스킹은 4-2)
- 검색 임베딩으로 약 0.5초 늘어남. 기록만 하고 5-5로

## 결과(2026-10-22)
- 첫 실행(3회)
  - m-13·m-20·m-22·m-24 PASS. m-22는 retrieve 단계, contexts doc_id=ext_park_abc.md, "반도체 장비" 포함. m-24는 retrieve output no_answer, contexts에 소개 자료 없음
  - **m-23 FAIL 3/3**: Haiku Supervisor가 "연구 분야가 뭐야?"를 "지원하지 않는 요청"으로 보고 하위 Agent를 부르지 않음
  - **m-14 FAIL 3/3**: 모델이 name에 "임수빈 이사"(프로젝트의 '성명 전체' 규칙)를 넘겨 DB에 이름이 "임수빈 이사"로 저장됨
- 고친 것(계획과 달라진 점)
  - `src/tools.py` `register_external_profile`: name 끝에 title이 붙어 있으면 떼어 내고 저장(코드로 정규화). 도구 설명도 "name은 직책을 뺀 이름"으로. 계획에서는 tools.py를 바꾸지 않기로 했으나, 모델에 맡기면 '성명 전체' 규칙과 충돌해 코드로 고침
  - `evaluation/check_tools.py`: "m-14 이름에 붙은 직책 떼기" 검사 추가(36 → 37)
  - `SUPERVISOR_PROMPT`: "사람이나 회사에 관한 질문은 모두 schedule_agent"(연구 분야 예시 포함), 지원하지 않는다고 답하는 경우를 "일정·회의·사람·회사와 전혀 관계없는 요청"으로 좁힘
- 수정 후 3회: m-13·m-14·m-20·m-22·m-23·m-24 18/18 PASS(m-14 DB 행 = 임수빈/이사/XYZ사/010-2222-3333/lim@xyz.example/외부 인물), 5.4~10.9초
- 회귀: m-01~m-12·m-21·m-07 13건 모두 PASS(m-01만 11.87초), check_tools.py 37개 PASS
