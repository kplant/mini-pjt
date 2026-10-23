# 계획: TASKS 6-2 제출

## Context
- 사용자 결정(2026-10-23): 폴더 이름(`mini-pjt_김상열`)은 바꾸지 않고, `mini-pjt` 저장소를 원격(`origin` https://github.com/kplant/mini-pjt.git)에 push해 제출
- ADR 0001은 `sds-ax-training/miniprj/`로 손으로 옮기는 제출을 전제로 쓰여 있어 고침

## 할 일
1. ADR 0001: 재사용 코드 복사 결정은 유지, 제출은 원격 push로. 받은 쪽은 README대로 .venv·DB·벡터DB를 새로 만듦
2. TASKS 6-2 문구와 확인 항목을 push 방식으로
3. 제출 전 확인: 비밀 값 추적 여부(.env·db/·chroma_db/ 미추적, AWS 키 패턴 없음), 서버 m-04 → 200
4. 커밋 `TASKS 6-2: 제출(원격 push)` 후 `git push origin master`, 원격과 로컬 커밋 비교

## 결과(2026-10-23)
- 추적 파일에 .env·sqlite·chroma 없음, `AKIA…` 패턴 없음(결과 JSON 포함)
- uvicorn + curl m-04: HTTP 200, 키 answer·contexts·trace, route=조율, 후보 3개
- push 결과는 커밋 뒤라 이 파일이 아니라 작업 보고에 남김
