# 계획: TASKS 3-3 일정 Agent 변경·취소·불참·승인 처리

## Context
- 확인 항목: m-08~m-12 실행 후 DB 상태가 expect와 일치
  - m-08(exec-kang) 수요일 협력사 미팅 11시로: 바로 반영, 답에 "11:00", 승인 대기 없음
  - m-09(sec-jung) 수요일 협력사 미팅 취소: exec-kang 승인 대기, 일정 그대로
  - m-10(sec-kim) 금요일 전략 리뷰 강민준 불참: exec-kang 승인 대기, 답에 "불참"
  - m-11(exec-kang) 승인 대기 목록: 답에 "예산 협의"
  - m-12(exec-kang) 예산 협의 참석 요청 승인: 승인 처리, 승인 대기 없음
- 도구·권한 규칙은 `src/tools.py`에 이미 있음. 일정 Agent에는 조회 도구 2개만 열려 있음(3-2)
- 흐름: tool_list_events로 event_id → 변경 도구. 승인은 tool_list_pending_approvals로 approval_id → tool_decide_approval

## 변경 파일 (2026-10-22 사용자 승인)
1. `src/tools.py`: `update_event`·`tool_update_event`의 `new_end`를 선택 인자로. 비우면 원래 길이 유지(끝 시각 계산을 코드가 함)
2. `evaluation/check_tools.py`: new_end 생략 시 11:00~12:00이 되는지 검사 1개 추가(35 → 36)
3. `src/agent.py`
   - `SCHEDULE_TOOL_NAMES`에 tool_update_event, tool_cancel_event, tool_mark_absent, tool_list_pending_approvals, tool_decide_approval 추가
   - `SCHEDULE_PROMPT`: event_id는 tool_list_events로 찾고 지어내지 않음, 끝 시각을 말하지 않으면 new_end 생략, 승인은 목록에서 approval_id를 찾은 뒤 결정, 분명하면 되묻지 않음(같은 이름 여러 개일 때만), applied=false·pending_approval_for면 "승인 대기"와 reason 전달, 변경 결과에 새 시각
   - 일정 Agent 설명과 `SUPERVISOR_PROMPT`에 "기존 일정 변경·취소·불참, 승인 대기 목록·승인·거절 → schedule_agent" 예시
   - 모듈 docstring 구현 범위
4. `README.md` 구현 범위 3-3까지
5. `TASKS.md` 3-3 `[x]`, 이 파일 끝에 결과

## 검증
1. m-08~m-12 각 3회(문항마다 reset_db): route=일정, refused=false, pending_approvals가 expect와 같음, must_include, DB 직접 조회
   - m-08: 협력사 미팅 10-28 11:00~12:00, 새 승인 대기 없음
   - m-09: 협력사 미팅 그대로, exec-kang '취소' 승인 대기 1건
   - m-10: 전략 리뷰의 강민준 상태 그대로, exec-kang '불참' 승인 대기 1건
   - m-11: DB 변화 없음
   - m-12: ap-01 '승인', 예산 협의의 강민준 '확정'
2. 회귀: m-01~m-03 각 1회, m-04~m-07·m-21 각 1회, check_tools.py 36개 PASS
3. 커밋 `TASKS 3-3: 일정 Agent 변경·취소·불참·승인`

## 위험
- 변경 문항은 조회 → 변경으로 모델 호출 3회 → 10초를 넘기 쉬움. 기록만 하고 5-5로
- '불참'·'11:00' 표현이 흔들리면 reason·새 시각을 코드로 덧붙이는 방안을 보고 후 적용

## 결과(2026-10-22, 사용자가 Sonnet 한도를 초기화한 뒤 실행)
- m-08~m-12 각 3회: 15/15 PASS(route=일정, refused=false, pending_approvals, must_include, DB 상태 모두 일치). 하위 Agent는 매번 Sonnet 4.5, Supervisor는 Haiku
  - m-08: list_events → update_event(new_end 생략), 협력사 미팅 11:00~12:00, 새 승인 대기 없음. "11:00~12:00으로 변경했습니다"
  - m-09: list_events → cancel_event, 일정 그대로, exec-kang '취소' 대기
  - m-10: list_events → mark_absent, 강민준 상태 '확정' 그대로, exec-kang '불참' 대기
  - m-11: list_pending_approvals, "예산 협의" 포함, DB 변화 없음
  - m-12: list_pending_approvals → decide_approval, ap-01 '승인', 강민준 '확정'
  - 응답 시간: 대부분 5.5~9초, 13.12초(m-08 1회차)·11.68초(m-12 2회차) 두 번 10초 초과
- 회귀: m-01~m-06·m-21·m-07 모두 PASS(m-01만 13.32초), check_tools.py 36개 PASS
- 계획과 달라진 점: 없음. 답변 표현을 코드로 보장하는 방안은 필요하지 않았음
