# k3s 매니페스트

| 파일 | 무엇 | 상태 |
|---|---|---|
| `deployment.yaml` | API 파드 | 서버에서 도는 것을 옮겨 적었다 — 바로 아래 |
| `showcase-autoaccept.yaml` | 시연 더미 자동 수락 봇 | 시연 동안만 — 적용·지우기는 파일 머리말 |
| `monitoring.yaml` · `grafana-dashboard-supersub-api.json` | 운영 관제(지표 수집 + 그래프) | **서버 미적용** — 아래 「운영 관제」 |

> **상태:** `deployment.yaml` 옮겨 적음 · 2026-09-15
> **확인:** `ssh supersub 'sudo k3s kubectl get deploy supersub-api-trial -o yaml'`와
> 대조 — `containers[0].command`·`image`·`envFrom`·`initContainers`가 같으면 맞다
> **메모:** 서버에서 실제로 돌던 것을 옮겨 적은 것뿐이다(미결 `jin` 32번). 이름·
> 네임스페이스 정리, Service/Ingress 도입 여부는 이번 범위 밖.

절차·CD 흐름의 정본은 `../../docs/deployment.md`(2절 「현재 배포」)다. 여기는
매니페스트 실물만 둔다.

## 적용 전에 필요한 것 (한 번씩)

이 Deployment는 Secret 둘을 전제로 한다 — 매니페스트에는 안 담는다(값을
커밋하면 안 되므로).

```bash
# 1. 설정값 — 키 목록의 정본은 ../../.env.example
kubectl create secret generic supersub-api-env --from-env-file=<서버의 .env>

# 2. Docker Hub 이미지 pull 자격 (private 저장소가 아니면 사실 불필요하지만
#    이미 이 이름으로 걸려 있어 그대로 둔다)
kubectl create secret docker-registry dockerhub-cred \
  --docker-username=<Docker Hub 사용자명> --docker-password=<토큰>
```

## 적용

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/supersub-api-trial
```

`strategy: Recreate`라 롤아웃 중 짧은 다운타임이 있다(`hostNetwork`라 포트
충돌 방지 목적 — `deployment.md` 2절 참고).

## 운영 관제 — Prometheus + Grafana

> **상태:** 진행 전(매니페스트만) · **서버 미적용** · 2026-09-23
> **확인:** `ssh supersub 'sudo k3s kubectl get ns monitoring'` → `NotFound` 면 아직 안 올렸다
> **메모:** 대시보드 식의 지표 이름·라벨은 서버의 실제 `/metrics`(2026-09-23)에서 확인했다.
> 로컬에서 한 것: 짜임 검사 · 로컬 k3s 모의 적용(`--dry-run=server --validate=strict`) ·
> PromQL 13식 문법 검사. 서버에서 떠 본 적은 없다.

API 파드의 `/metrics` 를 15초마다 모아 요청률·오류율·지연 분위수를 그린다. 요구사항
PER-003(조회 응답 P95 500ms 이내)을 **실측으로 판정하는 자리**다.

| 파일 | 무엇 |
|---|---|
| `monitoring.yaml` | Prometheus(보관 15일 또는 1GB 중 먼저 닿는 쪽) · Grafana(데이터 원본·대시보드 자동 등록) |
| `grafana-dashboard-supersub-api.json` | 대시보드 한 장 — 수집 상태 · 사용자 요청률 · 5xx 비율 · PER-003 판정 · 지연 P50/P95/P99 · 응답 코드별 · 사용자 대 워커 · 느린 경로 상위 5 · 메모리·CPU |

🔴 **바깥에 새 포트를 열지 않는다.** 둘 다 API 파드처럼 `hostNetwork` 로 떠서 서버의
`127.0.0.1`(Prometheus 9090 · Grafana 3000)에만 귀를 연다. 보안그룹·nginx 는 그대로 두고
SSH 터널로만 본다. `/metrics` 자체도 nginx 에서 바깥을 막았다(`deployment.md` 「`/metrics` 는
nginx 에서 막는다」).

helm 의 kube-prometheus-stack 을 쓰지 않은 이유: 서버 한 대(디스크 여유 9GB, 2026-09-23)에서
API 하나를 보는 데는 operator·node-exporter·alertmanager 까지 딸려 오는 것이 과하다. **경보는
없다** — 지금은 보는 화면만이다.

### 적용 전 확인 (서버에서)

```bash
sudo k3s kubectl get storageclass local-path   # 있어야 한다 — Prometheus 데이터(PVC)가 쓴다
sudo ss -ltn | grep -E ':(3000|9090)\b'         # 비어 있어야 한다 — 두 포트를 쓴다
df -h /                                         # 1GB 넘게 남아 있어야 한다 — 보관 상한이 1GB 다
```

### 적용 (서버에서, 이 폴더에서)

```bash
# 1. 네임스페이스 + 파일에 없는 둘. 비밀번호는 셸 기록에 안 남게 read -s 로 받는다
sudo k3s kubectl create namespace monitoring
read -rsp 'Grafana 관리자 비밀번호: ' GF_PW; echo
sudo k3s kubectl -n monitoring create secret generic grafana-admin --from-literal=password="$GF_PW"
unset GF_PW
sudo k3s kubectl -n monitoring create configmap grafana-dashboards \
  --from-file=supersub-api.json=grafana-dashboard-supersub-api.json

# 2. 나머지
sudo k3s kubectl apply -f monitoring.yaml
sudo k3s kubectl -n monitoring rollout status deploy/prometheus
sudo k3s kubectl -n monitoring rollout status deploy/grafana
```

> **떴는지 확인:** `curl -s 127.0.0.1:9090/api/v1/targets | grep -o '"health":"[a-z]*"'` →
> `"health":"up"` 둘(API · Prometheus 자신)

### 보기 (내 PC 에서)

```bash
ssh -N -L 3000:127.0.0.1:3000 supersub   # 켜 둔 채로
# 브라우저 http://localhost:3000 → admin / 위 비밀번호 → Super-Sub 폴더 → 「Super-Sub API — 운영 관제」
```

### PER-003 을 읽는 법

「PER-003 — 조회(GET) 중 0.5초 안에 끝난 비율 (1시간)」 칸이 **95% 이상이면 P95 가 500ms
안**이다. 경로별 히스토그램의 버킷 경계가 정확히 0.5초라 분위수를 근사하지 않고 그대로 판정한다.

**사용자 요청**은 워커 폴링(`/api/v1/internal/*`) · 수집기 자신의 `/metrics` · `/health` · 없는
경로(`none`)를 뺀 것이다 — Prometheus 가 15초마다 `/metrics` 를 두드리므로 빼지 않으면 요청률과
판정이 부풀려진다. 지연 P50/P95/P99 그래프는 경로 라벨이 없는 고해상도 히스토그램이라 워커
폴링이 섞인다(제목에 적어 두었다).

실측이 나오면 5장 PER-003 과 관리 지표(`tools/pages/gen_metrics.py` 의 `MEASURED`)에 옮긴다.

### 고칠 때

| 바꾼 것 | 반영 |
|---|---|
| 대시보드 JSON | ConfigMap 만 바꾼다 — 보통 1~2분 안에 Grafana 가 다시 읽는다(재시작 불필요) |
| `grafana-provisioning` | `rollout restart deploy/grafana` — `subPath` 로 꽂아서 자동 반영이 안 된다 |
| `prometheus-config` | `rollout restart deploy/prometheus` — 설정을 스스로 다시 읽지 않는다 |

```bash
# 대시보드 ConfigMap 바꾸기
sudo k3s kubectl -n monitoring create configmap grafana-dashboards \
  --from-file=supersub-api.json=grafana-dashboard-supersub-api.json --dry-run=client -o yaml \
  | sudo k3s kubectl apply -f -
```

### 지우기

```bash
sudo k3s kubectl delete namespace monitoring   # 수집한 지표(PVC)까지 함께 지워진다
```
