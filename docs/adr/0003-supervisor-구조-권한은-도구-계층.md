# Supervisor 구조로 가되, 권한은 도구 계층에서 막는다

업무가 늘어날 것(예: 출장, 회의실 예약)에 대비해, 도구 Agent 하나 대신 Supervisor와 업무별 하위 Agent 구조를 씁니다. Supervisor의 라우팅은 LLM이 하므로 결정적이지 않습니다. 그래서 권한 판단은 Supervisor나 Agent 프롬프트에 맡기지 않습니다. 대신 모든 일정 도구가 요청자를 받아 역할과 담당 관계, 비공개 여부를 직접 검사합니다. 이렇게 하면 라우팅이 틀려도 볼 수 없는 일정 내용은 반환되지 않습니다.

처음에는 Supervisor를 직접 만든 `StateGraph`로 구현하려 했습니다. 하지만 제출 규약이 "Agent 생성은 `create_agent`"로 정해져 있어서, Supervisor도 `create_agent`로 만듭니다. 하위 Agent 세 개(조율·일정·관리)는 도구로 감싸 Supervisor에 넘깁니다. 어느 하위 Agent 도구를 불렀는지가 응답 `trace`의 `route`가 됩니다.
