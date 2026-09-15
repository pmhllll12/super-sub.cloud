# k3s 매니페스트

> **상태:** `deployment.yaml`만 있음 · 2026-09-15
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
