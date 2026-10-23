# 임원 일정 관리 Agent 서버 이미지입니다(TASKS 6-4).
# 빌드: docker build -t mini-pjt .
# 실행: docker run -p 8000:8000 --env-file .env mini-pjt
# AWS 자격 증명(.env)은 이미지에 넣지 않고 실행할 때 넘깁니다. DB는 서버가 처음 뜰 때,
# 벡터DB(Chroma)는 첫 소개 자료 검색 때 Titan 임베딩으로 만듭니다(빌드 때는 자격 증명이 없음).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data ./data
COPY evaluation ./evaluation
COPY demo.py run.sh ./

ENV HOST=0.0.0.0 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["bash", "run.sh", "serve"]
