#!/usr/bin/env bash
# 계약 문서의 모든 경로를 성공·실패 양쪽으로 눌러본다.
#
#   bash smoke.sh
#
# 서버를 직접 띄웠다 내린다. 이미 8000 을 쓰고 있으면 BASE 를 넘겨서 재사용한다:
#   BASE=http://127.0.0.1:8000 bash smoke.sh
set -u
cd "$(dirname "$0")"

OWN_SERVER=0
if [ -z "${BASE:-}" ]; then
  BASE="http://127.0.0.1:8000"
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/ss-smoke-uvicorn.log 2>&1 &
  PID=$!
  OWN_SERVER=1
  for _ in $(seq 1 40); do
    curl -sS --max-time 2 "$BASE/health" >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

PASS=0
FAIL=0

# check <설명> <기대코드> <기대본문조각> <curl 인자...>
check() {
  local label="$1" want_status="$2" want_body="$3"; shift 3
  local out status body
  out=$(curl -sS -w $'\n%{http_code}' "$@")
  status=$(printf '%s' "$out" | tail -n1)
  body=$(printf '%s' "$out" | sed '$d')

  if [ "$status" = "$want_status" ] && printf '%s' "$body" | grep -q "$want_body"; then
    printf '  ✅ %-46s %s\n' "$label" "$status"
    PASS=$((PASS + 1))
  else
    printf '  ❌ %-46s %s (기대 %s / %s)\n' "$label" "$status" "$want_status" "$want_body"
    printf '     %s\n' "$body"
    FAIL=$((FAIL + 1))
  fi
}

echo "== 기동 =="
check "GET /health" 200 '"stub":true' "$BASE/health"

echo "== 인증: 성공 경로 =="
TOKEN=$(curl -sS -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@super-sub.example","password":"supersub2026"}' \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
if [ -n "$TOKEN" ]; then
  printf '  ✅ %-46s 토큰 획득\n' "POST /auth/login"; PASS=$((PASS + 1))
else
  printf '  ❌ %-46s 토큰 없음\n' "POST /auth/login"; FAIL=$((FAIL + 1))
fi

check "POST /auth/signup (새 이메일)" 201 '"nickname":"새사람"' \
  -X POST "$BASE/api/v1/auth/signup" -H 'Content-Type: application/json' \
  -d '{"email":"new@example.com","password":"password123","nickname":"새사람"}'

echo "== 인증: 실패 경로 =="
check "POST /auth/login (비밀번호 틀림)" 401 'INVALID_CREDENTIALS' \
  -X POST "$BASE/api/v1/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"demo@super-sub.example","password":"wrong-password"}'

check "POST /auth/login (없는 계정도 같은 code)" 401 'INVALID_CREDENTIALS' \
  -X POST "$BASE/api/v1/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"nobody@example.com","password":"whatever12"}'

check "POST /auth/signup (중복 이메일)" 409 'EMAIL_ALREADY_EXISTS' \
  -X POST "$BASE/api/v1/auth/signup" -H 'Content-Type: application/json' \
  -d '{"email":"demo@super-sub.example","password":"password123","nickname":"홍길동"}'

check "POST /auth/signup (비밀번호 8자 미만)" 422 'VALIDATION_ERROR' \
  -X POST "$BASE/api/v1/auth/signup" -H 'Content-Type: application/json' \
  -d '{"email":"a@example.com","password":"short","nickname":"짧아"}'

check "POST /auth/signup (이메일 형식 오류)" 422 'VALIDATION_ERROR' \
  -X POST "$BASE/api/v1/auth/signup" -H 'Content-Type: application/json' \
  -d '{"email":"not-an-email","password":"password123","nickname":"홍길동"}'

echo "== 내 정보 =="
check "GET /me (토큰 있음)" 200 '"nickname":"홍길동"' \
  "$BASE/api/v1/me" -H "Authorization: Bearer $TOKEN"

check "GET /me (토큰 없음)" 401 'UNAUTHORIZED' "$BASE/api/v1/me"

check "GET /me (토큰 틀림)" 401 'INVALID_TOKEN' \
  "$BASE/api/v1/me" -H "Authorization: Bearer garbage"

echo "== 선수 카드 =="
check "GET /me/card" 200 '"public_slug":"hong-gildong-4f2a"' \
  "$BASE/api/v1/me/card" -H "Authorization: Bearer $TOKEN"

check "GET /me/card (인증 없음)" 401 'UNAUTHORIZED' "$BASE/api/v1/me/card"

check "GET /cards/{slug} (인증 불필요)" 200 '"public_slug"' \
  "$BASE/api/v1/cards/hong-gildong-4f2a"

check "GET /cards/{slug} (없는 슬러그)" 404 'CARD_NOT_FOUND' \
  "$BASE/api/v1/cards/no-such-slug"

echo "== 설계 원칙 (부록 D.5) =="
CARD=$(curl -sS "$BASE/api/v1/cards/hong-gildong-4f2a")
if printf '%s' "$CARD" | grep -qiE '"(score|rating|stat|level|rank|grade|point)'; then
  printf '  ❌ %-46s 수치 필드가 있다\n' "카드에 능력치 수치 없음"; FAIL=$((FAIL + 1))
else
  printf '  ✅ %-46s\n' "카드에 능력치 수치 없음"; PASS=$((PASS + 1))
fi
if printf '%s' "$CARD" | grep -q '"earned"'; then
  printf '  ❌ %-46s earned 필드가 있다\n' "호칭에 미부여 표식 없음"; FAIL=$((FAIL + 1))
else
  printf '  ✅ %-46s\n' "호칭에 미부여 표식 없음"; PASS=$((PASS + 1))
fi

echo "== 공개 카드에 내부 id 가 새지 않는지 =="
if printf '%s' "$CARD" | grep -qE '^\{"id"|,"id":"[0-9a-f-]{36}","public_slug"'; then
  printf '  ❌ %-46s 카드 id 가 노출된다\n' "공개 카드에 카드 id 없음"; FAIL=$((FAIL + 1))
else
  printf '  ✅ %-46s\n' "공개 카드에 카드 id 없음"; PASS=$((PASS + 1))
fi

if [ "$OWN_SERVER" = "1" ]; then
  kill "$PID" 2>/dev/null
  wait "$PID" 2>/dev/null
  rm -f /tmp/ss-smoke-uvicorn.log
fi

echo
echo "통과 $PASS · 실패 $FAIL"
[ "$FAIL" -eq 0 ]
