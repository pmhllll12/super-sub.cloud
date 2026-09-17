# 백엔드 API 이미지. CD: `.github/workflows/backend-docker-build.yml` 가
# `main` 의 `fastapi/**` 변경을 빌드해 `pmhllll12/supersub:latest` 로 push 하고,
# `supersub` 서버의 `supersub-cd.timer` 가 새 digest 를 폴링해 재배포한다
# (미결 min 11번 · `www/docs/2026-09-09-K3S-harness.md`).
#
# 🔴 포트 8080 · `python:3.14-slim` 은 CD·Deployment 가 물고 있으니 바꾸지 않는다.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성을 먼저 — 앱 코드만 바뀔 때 이 레이어가 재사용된다.
# psycopg-binary·bcrypt·cryptography 는 manylinux 휠이 있어 빌드 도구가 필요 없다.
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# 🔴 **필요한 것만 넣는다.** `COPY . .` 는 docs·scripts·`CLAUDE.md`·Dockerfile
#    자신까지 이미지에 굽는다. `.env` 사고(min 11번) 뒤라 범위를 좁게 잡는다.
#    `alembic/` 은 남긴다 — 배포 때 `alembic upgrade head` 를 이미지 안에서 돈다.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# 루트로 돌지 않는다.
RUN useradd --system --uid 10001 supersub && chown -R supersub /app
USER supersub

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
