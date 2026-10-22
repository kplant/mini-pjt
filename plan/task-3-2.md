# 계획: TASKS 3-2 일정 Agent(조회·브리핑·특정 시각 조회) + Supervisor Haiku 1순위

## Context
- 확인 항목: m-01·m-02·m-03의 must_include / must_not_include
  - m-01(sec-kim, 내일 강민준 부사장): "주간 경영회의", "ABC사 미팅", "바쁨" 포함, "건강검진" 없음(비공개)
  - m-02(exec-kang, 내일 내 일정): 본인이라 "건강검진"까지 보임
  - m-03(sec-park, 목요일 윤서연 전무): "인사위원회", "바쁨" 포함, "가족 행사" 없음(비공개)
- 도구는 이미 있음: `list_events`·`get_event_at`이 권한을 검사하고 볼 수 없는 일정은 바쁨으로만 돌려줌. 남은 일은 Agent 연결, 프롬프트, 날짜 계산
- 추가 요청(3-1 결과, 2026-10-22 사용자 승인): 라우팅 호출로 m-04가 13.64초. Supervisor만 Haiku 1순위로 써서 라우팅 시간을 줄인다

## 변경 파일
1. `src/agent.py` (바뀐 부분만)
   - Supervisor 모델: `SUPERVISOR_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"`(.env `SUPERVISOR_MODEL_ID`가 우선). `supervisor_model_ids()` = Haiku + 나머지 `model_ids()`(중복 제외). `_model_setup(llm, ids=None)`에 후보 목록 인자. 하위 Agent는 그대로 `model_ids()`
   - `date_hints`에 이번 주·다음 주 요일별 날짜 추가(모델이 "목요일"을 계산하지 않게)
   - `SCHEDULE_PROMPT`: 도구 결과만 믿음, "내 일정"은 임원이면 본인·비서면 담당 임원, 시간순 제목, 바쁨 항목은 "HH:MM~HH:MM 바쁨"으로 시간과 '바쁨'만, 특정 시각은 `tool_get_event_at`
   - `build_schedule_agent`: `build_tools(ctx)["일정"]` 중 조회 2개(`SCHEDULE_TOOL_NAMES = tool_list_events, tool_get_event_at`)만. 3-3·3-4에서 이름 추가
   - `_build_sub_agent(ctx, prompt, tools, llm, checkpointer)`로 조율·일정 Agent 공통 구조를 묶음
   - `SUB_AGENTS`에 `schedule_agent: 일정` 추가, `SUPERVISOR_PROMPT` 다듬기
2. `TASKS.md` 3-2: "+ Supervisor는 Haiku 1순위", 확인에 "m-04 10초 이내, m-04~m-07·m-21 route 유지" 추가
3. `CLAUDE.md` 모델 설명, `README.md`: Supervisor Haiku 1순위 한 줄, 구현 범위 3-2까지
4. 새 파일·새 라이브러리 없음

## 검증
1. m-01·m-02·m-03 각 3회: route=일정, refused=false, must_include / must_not_include, 응답 시간. trace 도구 단계 output에 "건강검진"(m-01)·"가족 행사"(m-03) 없음
2. 라우팅 회귀(Haiku): m-04·m-05·m-06·m-21 route=조율 + 2-2 기준, m-07 두 턴 route=조율 + registered_for=[exec-kang], pending=[exec-yoon]
3. 응답 시간: m-04 10초 이내. Supervisor가 실제로 Haiku로 답했는지 검증 스크립트에서 따로 출력
4. check_tools.py 35개 PASS
5. 커밋 `TASKS 3-2: 일정 Agent 조회·브리핑, Supervisor Haiku`

## 위험
- Haiku가 "2번으로 해줘"를 잘못 보내면 m-07 실패 → Supervisor 프롬프트 보강 후 재확인
- '바쁨' 대신 다른 표현이 나오면 m-01·m-03 실패 → 3회 중 흔들리면 코드로 보장하는 방안을 보고

## 결과(2026-10-22)
- 첫 실행(수정 전 프롬프트)
  - m-01·m-02·m-03 각 3회 모두 PASS(route=일정, must_include / must_not_include, trace 도구 단계에도 "건강검진"·"가족 행사" 없음)
  - **Haiku 라우팅 오류 2건**: m-05("30분 미팅 후보 찾아줘")·m-06("미팅 잡아줘")을 일정으로 보냄
  - **m-07 2턴 미등록**: 대체된 Sonnet 4.6이 "회의 제목을 알려주시면…"이라고 되묻고 등록하지 않음
- 고친 것
  - `SUPERVISOR_PROMPT`에 라우팅 기준 두 줄(새 회의·후보 시간·등록 → coordination_agent, 기존 일정 조회·브리핑·특정 시각 → schedule_agent, 예시 포함)
  - `COORDINATION_PROMPT`에 "등록할 때 제목을 되묻지 않고, 없으면 '회의'로 등록"
- 수정 후 2회: m-01~m-06·m-21·m-07 16건 모두 PASS. Supervisor는 매번 Haiku로 답함. m-04 8.79초 / 8.62초
- check_tools.py 35개 PASS
- 계획과 달라진 점: 위 프롬프트 두 곳 보강. Supervisor 모델은 decision에 넣지 않고 검증 스크립트에서 `_invoke`를 감싸 확인함
- 남은 점(5-5): 이번 세션 내내 global Sonnet 4.5가 Agent 호출에서 간헐적으로 실패(일일 한도로 추정)해 하위 Agent가 Sonnet 4.6·Haiku로 대체되었고, 그때 응답이 10~15초로 늘었다. Sonnet 4.5가 답한 실행은 대부분 10초 안팎. 하위 Agent 모델 순서 조정은 5-5에서 결정
