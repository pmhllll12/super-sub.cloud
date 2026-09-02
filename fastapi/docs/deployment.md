# 백엔드 배포 준비

> **상태:** **구현됨 — SSH 터널로 도는 것까지 확인** · 2026-09-02
> **확인:** `ssh supersub 'systemctl is-active supersub-api'` → `active`,
> 터널을 열고 `curl -s localhost:8000/health` → `"status":"ok"`.
> **밖에서는 아직 안 보인다** — 보안 그룹은 22 만 열려 있다(6-8 절).
> **메모:** 여기 적힌 것은 **배포 환경이 생겼을 때 순서대로 밟는 절차**다. 로컬
> 개발에 필요한 것은 `.env.example` 이 안내한다.

아래 순서에는 이유가 있다. **1번은 마이그레이션보다 먼저**여야 하고, 2번이 빠지면
조용히 잘못 동작한다. **0번은 2026-09-02 에 서버가 생기면서 앞에 붙었다** — 거기 적힌 셋이 정해지기 전에는 1번을 시작할 수 없다.

---

## 0. 배포 대상 서버 — 무엇이 있고 무엇이 없나 (2026-09-02 확인)

EC2 인스턴스 하나가 생겼다(`ssh supersub` · 서울 리전 · t3.large · vCPU 2 · 메모리
7.8GB · **디스크 30GB** 중 28GB 여유). **접속 정보는 저장소에 두지 않는다** — 개인
`~/.ssh/config` 의 `supersub` 별칭으로 가리킨다.

**확인 명령** — 하나라도 `-` 면 그 항목이 미착수다.

```bash
ssh supersub 'for c in python3.14 psql nginx git; do printf "  %-10s %s\n" "$c" "$(command -v $c || echo -)"; done'
```

> ⚠️ 처음에는 `command -v psql python3.14` 로 적었는데 **오탐이었다.** `command -v` 는
> **하나만 찾아도 0 을 낸다** — 파이썬이 깔린 뒤로 psql 이 없는데도 통과했다.
> 항목별로 찍어서 눈으로 보게 바꿨다.

### 지금 상태

| 항목 | 실제 |
|---|---|
| OS | Amazon Linux 2023 (커널 6.18) |
| 파이썬 | ✅ **3.14.7** (2026-09-02 설치, 아래 참고). 배포판 기본은 3.9 이고 `dnf` 최신은 3.11 이다 |
| PostgreSQL | ✅ **18.6** (2026-09-02 설치, 6-1 절). 로컬 개발과 같은 계열이다 |
| `git` | ✅ 2.50 |
| 앱 | ✅ `supersub-api.service` 로 `127.0.0.1:8000` 에 떠 있다 (6-5 절) |
| `nginx`·`docker`·`gcc`·`make` | ❌ 아직 없다 |
| 열린 포트 | ❌ **22 만.** 80·443 은 닫혀 있다 — 확인은 SSH 터널로 한다 |

### ✅ 파이썬 3.14 는 넣었다 (2026-09-02)

배포판 저장소에 3.14 가 없어서 **`uv` 로 독립 실행형 빌드**를 받았다. 소스 빌드는
`gcc`·`make` 부터 깔아야 하고 2 vCPU 에서 10분 넘게 걸린다.

```bash
# 1) uv 바이너리만 받는다 (시스템 패키지를 건드리지 않는다. pip 이 없어서 이 편이 짧다)
curl -fsSL https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz -o /tmp/uv.tar.gz
tar -xzf /tmp/uv.tar.gz -C /tmp && install -m 0755 /tmp/uv-*/uv ~/.local/bin/uv

# 2) 🔴 **/opt 에 설치한다.** 홈이 drwx------ 라 홈 안에 두면 서비스 계정이 못 읽는다
sudo mkdir -p /opt/python
sudo env UV_PYTHON_INSTALL_DIR=/opt/python ~/.local/bin/uv python install 3.14
sudo ln -sfn /opt/python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14 /usr/local/bin/python3.14
```

**확인** — 서비스 계정 대역으로도 돌아가는지까지 본다.

```bash
python3.14 -V                                    # Python 3.14.7
sudo -u nobody /usr/local/bin/python3.14 -V      # 여기서 막히면 경로 권한 문제다
```

- 쓴 버전: `uv` 0.12.9 · CPython 3.14.7 (`ssl` 은 OpenSSL 3.5.8)
- `ssl`·`sqlite3`·`zlib`·`ctypes`·`lzma`·`readline`·`hashlib`·`venv` 전부 있고
  `python3.14 -m venv` 도 확인했다
- **로컬 개발은 3.14.4 다.** 같은 3.14 계열이라 문법·표준 라이브러리 차이는 없지만
  패치가 다르다는 것은 알고 있어야 한다
- 홈에 잠깐 받았던 사본은 지웠다 — **어느 인터프리터가 쓰이는지 헷갈리면 안 된다**

### ✅ DB 위치는 정해졌다 (2026-09-02) — 같은 인스턴스

비용이 들지 않고 오늘 안에 끝낼 수 있어서 골랐다. **나중에 RDS 로 옮길 수 있다** —
`DATABASE_URL` 하나만 바뀐다. 절차는 6절.

> 디스크는 앱·DB·백업이 공유한다. **2026-09-02 에 8GB → 30GB 로 늘려**(7-1 절)
> 한동안 여유가 있다. 영상 파일 자체를 서버에 두게 되면 그때 다시 본다.

### 🔴 남은 결정 — 80·443 을 언제 여는가

**⑴ (해소됨) DB 를 어디에 두는가.** RDS(관리형·`pgvector` 는 `rds_superuser` 로 생성)와 같은
인스턴스에 설치하는 방법이 있다. 디스크를 나눠 쓰므로 영상·분석 데이터가 크게 늘면
그때 다시 본다(2026-09-02 에 30GB 로 늘렸다). 비용이 걸린 결정이다.

**⑵ 80·443 을 열 것인가.** 보안 그룹 변경은 AWS 콘솔 권한이 필요하다. 열기 전에
1절(확장)·2절(환경변수)이 끝나 있어야 한다 — **설정이 빈 채로 노출되면 503 이 아니라
잘못 도는 상태가 될 수 있다**(2절 참고).

> 미결 항목 `jin` 8번으로 올려 두었다. **둘이 정해지기 전에는 1절부터 시작하지
> 않는다** — 지금까지 서버에 한 일은 파이썬 설치 하나뿐이다.

---

## 1. DB 확장을 먼저 만든다 — 마이그레이션 전에

🔴 **`CREATE EXTENSION vector` 는 슈퍼유저만 할 수 있다.** 앱 계정으로는 안 된다.

`pgvector` 는 SFR-005(유사 선수 검색)가 쓸 확장이다. 확장이 없으면 `vector` 타입을
참조하는 마이그레이션이 `type "vector" does not exist` 로 **도중에** 멈춘다 —
스키마가 반쯤 올라간 상태가 된다.

```sql
-- 슈퍼유저로 (로컬: postgres · Aurora/RDS: rds_superuser)
CREATE EXTENSION IF NOT EXISTS vector;
```

로컬(WSL)에서는 이렇게 한다.

```bash
wsl.exe -d Ubuntu-26.04 -u root -- su - postgres -c "psql -d supersub -c 'CREATE EXTENSION IF NOT EXISTS vector'"
```

**확인** — 앱 계정으로 접속해 `installed_version` 이 나오면 된 것이다.

```sql
select name, default_version, installed_version
from pg_available_extensions where name = 'vector';
-- installed_version 이 NULL 이면 아직 안 만들어진 것이다
```

### 왜 마이그레이션에 넣지 않는가

**확장마다 필요한 권한이 다르다.** `trusted = true` 로 표시된 확장은 DB 소유자면
만들 수 있지만, **`vector` 는 trusted 가 아니라 슈퍼유저여야 한다.** 2026-09-01 에
로컬 PostgreSQL 18 에서 실측한 결과다 (`supersub` 는 DB 소유자, 슈퍼유저 아님).

| 시도 | 결과 |
|---|---|
| `CREATE EXTENSION hstore` (trusted) | 만들어졌다 |
| `CREATE EXTENSION postgres_fdw` (trusted 아님) | `permission denied to create extension` |

⚠️ **컨테이너로 띄운 PostgreSQL 에서 통과한 것은 근거가 못 된다.** 초기 사용자가
슈퍼유저인 경우가 많아 거기서는 조용히 성공한다. 그래서 권한이 아니라 **글자로**
막는다 — `tests/test_architecture.py` 의 `TestMigrationPrivileges` 가 마이그레이션
파일에 `CREATE EXTENSION` 이 들어가면 실패시킨다. **그 검사를 지우지 말 것.**

> `alembic check` 는 확장을 보지 않는다. 확장이 빠져도 거기서는 경고가 안 나온다.

---

## 2. 환경변수 — 빠뜨리면 조용히 잘못 도는 것들

`fastapi/.env.example` 이 전체 목록이다. 여기서는 **배포에서 특히 주의할 것**만 적는다.

| 키 | 안 넣으면 | 방향 |
|---|---|---|
| `APP_ENV` | 🔴 기본값이 `local` 이라 **`/docs`·`/openapi.json` 이 열린다** | fail-**open** |
| `ADMIN_EMAILS` | 회원 관리 admin 이 통째로 403 | fail-**closed** |
| `JWT_SECRET` | 로그인이 503(`AUTH_NOT_CONFIGURED`). 조용한 기본값은 두지 않았다 | fail-closed |
| `GOOGLE_CLIENT_IDS` | 구글 로그인이 503. **플랫폼마다 클라이언트 ID 가 다르니 쉼표로 전부** | fail-closed |

🔴 **`APP_ENV` 만 방향이 반대다.** 다른 것은 빠지면 기능이 멈춰서 바로 드러나는데,
이것은 빠지면 **문서가 공개된 채로 정상 동작한다.** 배포 직후 확인한다.

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<배포주소>/docs   # 404 여야 한다
```

---

## 3. 마이그레이션

```bash
alembic upgrade head
alembic check        # "No new upgrade operations detected." 여야 한다
```

`create_all` 을 쓰지 않는다 — 마이그레이션이 스키마의 정본이다.

---

## 4. 리버스 프록시·로드밸런서 뒤에 둘 때

> **주소는 `api.supersub-ai.com` 으로 정했다**(2026-09-02). 도메인 관리는
> 박민호이므로 A 레코드와 탄력적 IP 는 그쪽에서 만든다 — 미결 8번.
> 포트 개방은 **아직 하지 않기로 했다**. 지금은 SSH 터널로 쓴다(6-6 절).

🔴 **`X-Forwarded-For` 를 신뢰하도록 설정하지 않으면** 인증 로그의 `client` 와
**요청 제한(SEC-009)의 키가 전부 LB 주소가 된다.** 즉 모든 사용자가 한 덩어리로
묶여 서로의 제한에 걸린다.

같은 이유로 DB 접속은 `sslmode=verify-full` 을 쓴다. 기본값으로 둔 `require` 는
**암호화만 하고 인증서를 검증하지 않아** 중간자 공격을 막지 못한다.

```
DATABASE_URL=postgresql://<user>:<pw>@<host>:5432/<db>?sslmode=verify-full
```

---

## 5. 알고 넘어가는 한계

배포를 막지는 않지만 **모르고 있으면 나중에 원인을 못 찾는 것들**이다.

| 무엇 | 내용 |
|---|---|
| 요청 제한이 **프로세스 안에서만** 센다 | 워커가 여럿이면 워커마다 따로 센다. 실효 한도가 워커 수만큼 늘어난다 (5장 SEC-009) |
| 삭제 연쇄가 **DB 까지만** | 객체 저장소가 정해지지 않아 원본·썸네일·추출 프레임이 남는다 (5장 SEC-006 · ASM-003) |
| `Retry-After` 헤더가 없다 | 429 응답에 재시도 시점을 싣지 않는다. 클라이언트가 즉시 재시도하지 않도록 별도 합의가 필요하다 |

## 6. 실제로 밟은 순서 (2026-09-02, SSH 터널까지)

같은 인스턴스에 PostgreSQL 을 두기로 했고(비용 없음), 보안 그룹은 열지 않았다.
**밖에서는 아직 안 보인다** — 확인은 SSH 터널로 한다.

### 6-1. PostgreSQL 18

```bash
sudo dnf install -y git postgresql18-server postgresql18
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
```

로컬 개발과 **같은 18.x** 다. 계정과 DB 를 만든다.

```bash
sudo -u postgres psql -c "create role supersub login password '<생성한 값>'"
sudo -u postgres createdb -O supersub supersub
```

🔴 **`pg_hba.conf` 를 고쳐야 붙는다.** 기본이 `ident` 라 비밀번호 접속이 거부된다.
`127.0.0.1/32` 와 `::1/128` 의 **일반 접속만** `scram-sha-256` 으로 바꾼다
(replication 줄은 건드리지 않는다). 원본은 `pg_hba.conf.bak` 에 남겼다.

```bash
sudo systemctl reload postgresql
psql "$DATABASE_URL" -tAc "select current_user"   # supersub 이 나오면 된다
```

### 6-2. 코드와 의존성

```bash
git clone -b jin https://github.com/pmhllll12/super-sub.cloud.git ~/supersub/app
cd ~/supersub/app/fastapi
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
```

고정본(`requirements.lock.txt`)을 쓴다. **cp314 휠이 전부 있어 빌드가 없었다** —
`gcc` 를 깔지 않아도 됐다.

### 6-3. 설정

`~/supersub/app/fastapi/.env` 를 `0600` 으로 만든다. `.gitignore` 에 걸리는지
`git check-ignore` 로 확인했다.

| 키 | 넣은 값 |
|---|---|
| `APP_ENV` | `production` — **빠지면 `/docs` 가 열린다**(2절) |
| `DATABASE_URL` | `postgresql://supersub:…@127.0.0.1:5432/supersub` |
| `JWT_SECRET` | `openssl rand -base64 48` |
| `ADMIN_EMAILS` | **비어 있다** → 회원 관리 admin 은 403. 쓰려면 이메일을 넣는다 |
| `GOOGLE_CLIENT_IDS` | 비어 있다 → 구글 로그인은 503 |

### 6-4. 마이그레이션

```bash
set -a; . .env; set +a
.venv/bin/alembic upgrade head
```

**빈 DB 에서 처음부터 끝까지 돌았다** — 20 테이블, `sport` 3행, `position` 11행.

### 6-5. systemd

`/etc/systemd/system/supersub-api.service` 로 등록했다. 요점 셋이다.

- `EnvironmentFile` 로 `.env` 를 읽는다 — 설정이 한 곳에서만 온다
- `--host 127.0.0.1` — **밖에 열지 않는다.** 공개는 nginx 를 앞에 두고 그때 한다
- `After=postgresql.service` — DB 가 먼저 떠야 한다

```bash
sudo systemctl enable --now supersub-api
sudo systemctl is-active supersub-api     # active
sudo journalctl -u supersub-api -n 20     # 안 뜨면 여기부터 본다
```

### 6-6. 확인 — SSH 터널

```bash
ssh -f -N -L 8000:127.0.0.1:8000 supersub
curl -s http://127.0.0.1:8000/health
# {"status":"ok","env":"production","db_configured":true,"stub":false}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/docs   # 404 여야 한다
```

가입 → 로그인 → 카드 생성 → 팀 → 경기 등록 → 목록 → 공개 카드(인증 없이)까지
실제로 돌려 보고 전부 통과했다. **DB 에 쓰고 읽는 경로가 열렸다는 뜻이다.**

### 6-7. 다음에 코드를 올릴 때

```bash
ssh supersub 'cd ~/supersub/app && git pull && cd fastapi \
  && .venv/bin/pip install -q -r requirements.lock.txt \
  && set -a && . .env && set +a && .venv/bin/alembic upgrade head' \
  && ssh supersub 'sudo systemctl restart supersub-api'
```

마이그레이션이 실패하면 **재시작하지 않는다** — 위 명령이 `&&` 로 이어진 이유다.

### 6-8. 아직 안 한 것

| 무엇 | 왜 |
|---|---|
| **80·443 개방 · nginx · TLS** | 지금은 SSH 터널로만 본다. 열 때 순서는 4절 |
| **`pgvector`** | AL2023 저장소에 **패키지가 없다.** 지금 마이그레이션은 `vector` 를 안 써서 없이도 돌았다 — `player_vector` 가 들어올 때 소스 빌드(`gcc` 필요)를 해야 한다 |
| ~~백업~~ | ✅ 2026-09-02 에 걸었다 — 7절. **다만 같은 디스크에 쌓인다**(밖으로 옮기는 것은 별도) |
| **로그 회전·모니터링** | journald 기본값에 기대고 있다 |

---

## 7. 백업 (2026-09-02)

하루 한 번 `pg_dump` 로 뜬다. **`cronie` 를 깔지 않고 systemd 타이머를 썼다** —
앱 서비스와 같은 방식이라 로그가 journald 한 곳에 모이고 패키지가 늘지 않는다.

| | |
|---|---|
| 언제 | 매일 **18:20 UTC = 03:20 KST** (서버 시간대는 UTC 다) |
| 무엇 | `pg_dump -Fc --no-owner --no-privileges` (압축 custom 포맷) |
| 어디 | `/var/backups/supersub/supersub-<날짜>-<시각>.dump` (0700 디렉터리 · 0600 파일) |
| 얼마나 | **14개**(2주치). 지금 한 개가 35KB 다 |
| 놓쳤을 때 | `Persistent=true` — 서버가 꺼져 있었으면 켜진 뒤 한 번 돈다 |

```bash
systemctl list-timers supersub-backup.timer    # 다음 실행 시각
sudo systemctl start supersub-backup.service   # 지금 한 번
journalctl -u supersub-backup -n 20            # 결과·실패 이유
ls -lt /var/backups/supersub | head            # 최근 파일이 어제 것보다 새로운가
```

### 순서가 중요한 곳 하나

스크립트는 **먼저 뜨고 나중에 지운다.** 반대로 하면 새 백업이 실패한 날 옛 백업까지
사라진다. 쓰는 중에 죽어도 반쪽 파일이 남지 않도록 `.part` 로 받아서 옮긴다.

### 🔴 복원까지 해봤다 — 안 해본 백업은 백업이 아니다

임시 DB(`restorecheck`)를 만들어 넣고 원본과 대조했다. **운영 DB 는 건드리지 않는다.**

```bash
DUMP=$(ls -1t /var/backups/supersub/supersub-*.dump | head -1)
sudo -u postgres createdb -O supersub restorecheck
pg_restore --no-owner --no-privileges -d "${DATABASE_URL%/supersub}/restorecheck" "$DUMP"
# 원본과 대조: 테이블 수 · 주요 행 수 · alembic_version
sudo -u postgres dropdb restorecheck
```

2026-09-02 결과 — **테이블 20 · user 1 · team 1 · match 1 · position 11 ·
alembic `69f3d0e97ffd`** 가 양쪽 동일했다.

### 7-1. 디스크를 늘렸을 때 (2026-09-02, 8GB → 30GB)

콘솔에서 EBS 볼륨 크기를 바꾸면 **디스크만 커지고 파일시스템은 그대로다.** OS 안에서
두 단계를 더 밟아야 실제로 쓸 수 있다.

```bash
lsblk                       # 디스크는 30G 인데 nvme0n1p1 이 8G 면 아직이다
sudo growpart /dev/nvme0n1 1   # 1) 파티션을 디스크 끝까지
sudo xfs_growfs -d /           # 2) 파일시스템을 파티션 끝까지 (루트는 xfs 다)
df -h /                     # 30G 로 보이면 끝
```

- **마운트한 채로 된다.** 재부팅도 서비스 중단도 없었다 — 확장 뒤 `postgresql`·
  `supersub-api` 가 그대로 `active` 였고 `/health` 도 200 이었다
- 루트가 `ext4` 인 이미지라면 2단계가 `resize2fs /dev/nvme0n1p1` 이다.
  `findmnt -no FSTYPE /` 로 먼저 확인한다
- **줄이는 것은 안 된다.** EBS 는 확대만 되고, 되돌리려면 스냅샷에서 새로 만들어야 한다

> 늘리기 전에 백업이 있는지 본다. 디스크를 건드리는 작업이라 흔치는 않아도
> 되돌릴 수단이 있어야 한다 — 7절의 `pg_dump` 가 그것이다.

### 이 백업이 막아 주지 못하는 것

🔴 **같은 디스크에 쌓인다.** 실수로 지운 데이터를 되돌리는 데는 쓸 수 있지만
**인스턴스가 통째로 죽으면 백업도 같이 죽는다.** 재해 복구가 되려면 밖으로 옮겨야
하고(S3 등) 그건 비용·권한이 걸린 별도 결정이다.

디스크(30GB)를 앱·DB·백업이 나눠 쓴다. 지금은 35KB 짜리 14개라 무시할 수 있지만,
영상 메타·분석 결과가 쌓이면 **보관 개수와 위치를 다시 봐야 한다.**

---

## 8. 인스턴스를 껐다 켤 때 (2026-09-02)

비용 때문에 주기적으로 끈다. **서비스는 알아서 돌아온다** — `postgresql`·
`supersub-api`·`supersub-backup.timer` 가 전부 `enabled` 라 부팅하면 스스로 뜬다.

```bash
ssh supersub 'systemctl is-enabled postgresql supersub-api supersub-backup.timer'
# 셋 다 enabled 여야 한다. disabled 가 보이면 그건 껐다 켠 뒤 안 뜬다는 뜻이다
ssh supersub 'systemctl is-active postgresql supersub-api'   # 켠 뒤 확인
```

🔴 **탄력적 IP 가 없으면 공인 IP 가 바뀐다.** 켤 때마다 새 주소를 받으므로
`~/.ssh/config` 의 `HostName` 도, DNS 레코드도 어긋난다. 2026-09-02 에 붙이기로
했다(미결 8번, 박민호).

- 꺼져 있는 동안 **EBS 요금은 계속 나간다** — 디스크는 남아 있다
- 탄력적 IP 는 **인스턴스가 꺼져 있는 동안 과금**된다. 자주 끄면 알고 있어야 한다
- 백업 타이머는 `Persistent=true` 라 꺼져 있어 놓친 실행을 **켠 뒤 한 번** 돈다

### 주소가 바뀌었을 때

```bash
# 새 IP 를 콘솔에서 확인한 뒤
sed -i 's/^\(\s*HostName\).*/\1 <새 IP>/' ~/.ssh/config   # supersub 항목
ssh-keygen -R <옛 IP>                                      # known_hosts 정리
```

---
