# AWS 배포 — **콘솔 수동 생성** 판

[`README.md`](README.md)의 1\~3장(S3·IAM·VPC·EC2 생성)을 **AWS 콘솔 클릭 순서**로
옮긴 것이다. CLI 자격증명을 만들지 못하는 상황에서 쓴다.

**4장부터는 이 문서가 아니라 [`README.md`](README.md)로 돌아간다.** 거기서부터는
EC2 안에서 SSH로 하는 작업이라 콘솔이 필요 없다.

> **CLI가 되면 그쪽이 낫다.** 클릭 수십 번을 안 해도 되고, 설정이 맞는지
> 확인 명령으로 바로 검증된다. 이 문서는 대안이지 권장안이 아니다.

---

## 시작 전

- 리전이 **아시아 태평양(서울) `ap-northeast-2`** 인지 우측 상단에서 확인한다.
  **모든 단계에서 같아야 한다** — 리전이 섞이면 EC2가 버킷을 못 보거나
  리전 간 전송료가 붙는다.
- 계정 `0706-0555-3723`은 **팀 프로젝트와 공유하는 계정**이다. 격리 수준과
  그 한계는 [`README.md`](README.md) 첫머리를 볼 것.
- 콘솔 화면의 문구·배치는 AWS가 수시로 바꾼다. **버튼 이름이 조금 달라도
  하는 일이 같으면 그대로 진행한다.**

> 🔴 **[5-1 할당량 확인](#5-1-할당량-먼저-확인)을 제일 먼저 한다.** 증액이
> 필요하면 승인에 수 시간\~며칠 걸리고 그동안 EC2를 못 만든다. 신청만 걸어 두고
> 1\~4장(S3·IAM·VPC·보안그룹)을 진행하면 기다리는 시간이 겹친다. 1\~4장은
> 전부 무료거나 거의 무료라 먼저 만들어 둬도 손해가 없다.

### 필요한 권한 — 먼저 확인할 것

이 런북은 **계정에 리소스를 만들 수 있는 권한**을 가정한다. 제한된 IAM 사용자로는
중간에 막힌다. 2026-09-02에 `ho`로 실제로 막혔다 —
`servicequotas:ListAWSDefaultServiceQuotas` 액세스 거부.

| 장 | 필요한 것 | 없으면 |
|---|---|---|
| 5-1 할당량 | `servicequotas:ListAWSDefaultServiceQuotas`, `RequestServiceQuotaIncrease` | GPU 할당량을 보지도 신청하지도 못한다 |
| 1 S3 | `s3:CreateBucket`, `PutBucketPolicy`, `PutBucketVersioning`, `PutEncryptionConfiguration` | 버킷을 못 만든다 |
| 2 IAM | `iam:CreateRole`, `CreatePolicy`, `AttachRolePolicy`, `PassRole` | 역할을 못 만든다 → **2-C로 우회 가능** |
| 3 VPC | `ec2:CreateVpc`, `CreateSubnet`, `CreateInternetGateway`, `CreateRouteTable`, `CreateVpcEndpoint` | VPC를 못 만든다 → 기본 VPC로 우회 가능(격리 포기) |
| 4 보안그룹 | `ec2:CreateSecurityGroup`, `AuthorizeSecurityGroupIngress` | 우회 불가 |
| 5 EC2 | `ec2:RunInstances`, `CreateKeyPair`, `iam:PassRole` | 우회 불가 |

**우회 가능한 것은 2장(IAM 역할)과 3장(VPC)뿐이다.** 나머지가 막히면 계정
관리자에게 권한을 받거나 대신 만들어 달라고 해야 한다 — 미결 항목에 올릴 것.

확인은 **IAM → 사용자 → 해당 사용자 → 권한** 탭에서 붙은 정책을 보면 된다.

---

## 1. S3 버킷

### 1-1. 버킷 만들기

**S3 → 버킷 → 버킷 만들기**

| 항목 | 값 |
|---|---|
| 버킷 유형 | 범용 |
| 버킷 이름 | `supersub-ai-070605553723` |
| 리전 | 아시아 태평양(서울) ap-northeast-2 |
| 객체 소유권 | ACL 비활성화됨 (권장) — 기본값 |
| **모든 퍼블릭 액세스 차단** | **체크 유지** (기본값) |
| 버킷 버저닝 | **활성화** |
| 기본 암호화 | 서버 측 암호화(SSE-S3) + **버킷 키 활성화** |

버킷 이름에 계정번호를 붙이는 것은 S3 이름이 **전 세계에서 유일**해야 하기
때문이다. 이미 쓰이는 이름이면 거부된다.

**버킷 버저닝**은 기본이 "비활성화"라 직접 켜야 한다. 리포트를 덮어써도
이전 것이 남는다.

→ **버킷 만들기** 클릭

### 1-2. 폴더 3개

만든 버킷을 열고 **폴더 만들기**로 세 개를 만든다.

```
videos/     원본 영상 (입력)
models/     EXAONE 가중치
reports/    분석 리포트 (출력)
```

> S3에 진짜 폴더는 없고 키 접두사일 뿐이라, 사실 안 만들어도 업로드하면
> 생긴다. 그래도 만들어 두면 콘솔에서 구조가 보이고 IAM 정책과 눈으로 대조된다.

### 1-3. 평문 HTTP 거부 (버킷 정책)

버킷 → **권한** 탭 → **버킷 정책** → **편집** → 아래를 붙여넣고 저장.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::supersub-ai-070605553723",
        "arn:aws:s3:::supersub-ai-070605553723/*"
      ],
      "Condition": { "Bool": { "aws:SecureTransport": "false" } }
    }
  ]
}
```

**확인**: 권한 탭에서 "모든 퍼블릭 액세스 차단: 켜기", 속성 탭에서
"버킷 버저닝: 활성화됨", "기본 암호화: SSE-S3"가 보이면 된다.

---

## 2. IAM 역할 — EC2가 S3를 읽고 쓰게

**이 장이 막히면 건너뛰어도 된다.** 권한이 없어 역할을 못 만들면 아래
"2-C. 역할을 못 만들 때"로 간다.

### 2-1. 정책 만들기

**IAM → 정책 → 정책 생성 → JSON** 탭에 붙여넣는다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyOurPrefixes",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::supersub-ai-070605553723",
      "Condition": {
        "StringLike": { "s3:prefix": ["videos/*", "models/*", "reports/*"] }
      }
    },
    {
      "Sid": "ReadInputsAndModel",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": [
        "arn:aws:s3:::supersub-ai-070605553723/videos/*",
        "arn:aws:s3:::supersub-ai-070605553723/models/*"
      ]
    },
    {
      "Sid": "WriteReports",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::supersub-ai-070605553723/reports/*"
    }
  ]
}
```

정책 이름: `supersub-s3`

**`videos/`에 쓰기 권한이 없는 것이 의도다.** 영상 업로드는 사람이 하고 EC2는
읽기만 한다 — 인스턴스가 털려도 원본을 못 지운다. 모델 업로드(5장)도
`models/`에 쓰기가 없으므로 **사람이 콘솔이나 다른 자격증명으로** 올려야 한다.

### 2-2. 역할 만들기

**IAM → 역할 → 역할 생성**

| 항목 | 값 |
|---|---|
| 신뢰할 수 있는 엔터티 유형 | **AWS 서비스** |
| 사용 사례 | **EC2** |
| 권한 정책 | 방금 만든 `supersub-s3` 검색해 체크 |
| 역할 이름 | `supersub-ai-ec2` |

→ **역할 생성**

> 콘솔로 EC2용 역할을 만들면 **인스턴스 프로파일이 자동으로 같이 생긴다.**
> CLI 판에서 `create-instance-profile`을 따로 부르는 그 단계다.

### 2-C. 역할을 못 만들 때

`ho`에게 IAM 권한이 없어 위가 막히면 **역할 없이 진행한다.** 대신 EC2 안에서
`aws configure`로 키를 넣는다 — [`README.md`](README.md)의 2-B 그대로다.
그 경우 5-3(인스턴스 시작)에서 IAM 인스턴스 프로파일 칸을 **비워 두면** 된다.

코드는 어느 쪽이든 그대로 동작한다. `storage.py`가 boto3 기본 자격증명 체인을
쓰기 때문에 역할이든 키든 구분하지 않는다.

---

## 3. VPC — **추가 비용 없음**

**VPC → VPC 생성**에서 **"VPC 등"(VPC and more)** 을 고른다. 마법사가 서브넷·
인터넷 게이트웨이·라우팅 테이블을 한 번에 만들어 준다.

| 항목 | 값 | 비고 |
|---|---|---|
| 생성할 리소스 | **VPC 등** | |
| 이름 태그 자동 생성 | `supersub-ai` | 모든 리소스에 접두사로 붙는다 |
| IPv4 CIDR | `10.20.0.0/16` | 기본 VPC(172.31.x)와 겹치지 않게 |
| IPv6 CIDR | 없음 | |
| 테넌시 | 기본값 | |
| 가용 영역(AZ) 수 | **1** | |
| 퍼블릭 서브넷 수 | **1** | |
| 프라이빗 서브넷 수 | **0** | |
| **NAT 게이트웨이** | **없음** | 🔴 **여기만 틀리면 월 $45가 붙는다** |
| VPC 엔드포인트 | **S3 게이트웨이** | 무료. 켜 두는 편이 낫다 |
| DNS 옵션 | 두 개 모두 체크 | 호스트 이름·확인 활성화 |

→ **VPC 생성**

**돈이 드는 것은 NAT 게이트웨이뿐이고 우리는 안 쓴다.** VPC·서브넷·라우팅
테이블·인터넷 게이트웨이·보안 그룹·S3 게이트웨이 엔드포인트는 전부 무료다.
퍼블릭 서브넷에 인스턴스를 두고 인터넷 게이트웨이로 직접 나간다.

**확인**: 생성 후 리소스 맵에 `supersub-ai-vpc`, `supersub-ai-subnet-public1-...`,
`supersub-ai-igw`, `supersub-ai-rtb-public`, S3 엔드포인트가 보이면 된다.
**NAT 게이트웨이가 목록에 있으면 잘못 만든 것이다** — 지우고 다시 한다
(있는 동안 과금된다).

---

## 4. 보안 그룹

**EC2 → 보안 그룹 → 보안 그룹 생성**

| 항목 | 값 |
|---|---|
| 이름 | `supersub-ai-sg` |
| 설명 | `Super-Sub AI agent` |
| **VPC** | **`supersub-ai-vpc`** ← 기본 VPC가 선택돼 있으니 반드시 바꾼다 |

**인바운드 규칙 — 하나만 추가한다.**

| 유형 | 포트 | 소스 |
|---|---|---|
| SSH | 22 | **내 IP** (드롭다운에 "내 IP"가 있다) |

아웃바운드는 기본값(전체 허용) 그대로 둔다 — 모델·패키지를 받아야 한다.

🔴 **8000(vLLM)은 절대 열지 않는다.** vLLM OpenAI 서버는 **인증이 없어서**,
열리는 순간 누구나 GPU를 쓸 수 있다. 127.0.0.1에 묶여 있고 밖에서 봐야 하면
SSH 터널을 쓴다(README.md 참고).

8080(`api.py`)도 지금은 열지 않는다. 필요해지면 그때 "내 IP"로 추가한다.

---

## 5. EC2 인스턴스

### 5-1. 할당량 먼저 확인

**신규·소규모 계정은 G 계열 vCPU 할당량이 0인 경우가 많다.** 그러면 인스턴스
시작이 거부된다. 먼저 본다.

**Service Quotas → AWS 서비스 → Amazon EC2** → `Running On-Demand G` 검색
→ **"Running On-Demand G and VT instances"** 의 적용된 계정 수준 할당량 확인

g4dn.xlarge는 vCPU 4개라 **4 이상**이어야 한다. 0이면 같은 화면에서
**계정 수준에서 증가 요청** → 4 이상으로 신청한다. **승인에 수 시간\~며칠
걸리고 AWS가 결정한다** — 그동안 1\~4장(S3·IAM·VPC·보안그룹)은 이미 만들어
뒀으니 승인되면 여기부터 이어서 하면 된다.

### 5-2. 키 페어

**EC2 → 키 페어 → 키 페어 생성**

| 항목 | 값 |
|---|---|
| 이름 | `supersub-ai` |
| 키 페어 유형 | RSA |
| 프라이빗 키 형식 | **`.pem`** (OpenSSH — WSL에서 쓴다) |

생성하면 `.pem`이 **Windows 다운로드 폴더로 내려간다. 다시 못 받는다.**

WSL에서 SSH로 쓰려면 옮기고 권한을 조여야 한다 (권한이 느슨하면 ssh가 거부한다):

```bash
mkdir -p ~/.ssh
cp /mnt/c/Users/hi/Downloads/supersub-ai.pem ~/.ssh/
chmod 400 ~/.ssh/supersub-ai.pem
```

### 5-3. 인스턴스 시작

**EC2 → 인스턴스 → 인스턴스 시작**

| 항목 | 값 |
|---|---|
| 이름 | `supersub-ai` |
| **AMI** | **모든 AMI 찾아보기** → `Deep Learning OSS Nvidia Driver AMI GPU PyTorch` 검색 → **Ubuntu 22.04** 최신 버전 |
| 인스턴스 유형 | **`g4dn.xlarge`** |
| 키 페어 | `supersub-ai` |

**네트워크 설정 → 편집** (기본값이 기본 VPC라 반드시 연다)

| 항목 | 값 |
|---|---|
| VPC | **`supersub-ai-vpc`** |
| 서브넷 | `supersub-ai-subnet-public1-...` |
| 퍼블릭 IP 자동 할당 | **활성화** |
| 방화벽 | **기존 보안 그룹 선택** → `supersub-ai-sg` |

**스토리지 구성**

| 항목 | 값 |
|---|---|
| 크기 | **150 GiB** |
| 볼륨 유형 | gp3 |
| 암호화 | 활성화 |

> **150GB인 이유**: DLAMI 자체가 50\~90GB를 쓴다. 여기에 HuggingFace 캐시
> (EXAONE + RT-DETR + ViTPose)와 임시 영상이 더해진다. 100GB로 시작하면
> 모델 두어 개 받다가 꽉 찬다. gp3는 GB당 과금이라 50GB 더 잡아도 월 몇 달러다.

**고급 세부 정보** (펼쳐야 보인다)

| 항목 | 값 |
|---|---|
| IAM 인스턴스 프로파일 | `supersub-ai-ec2` (2-C로 갔으면 **비워 둠**) |

→ **인스턴스 시작**

🔴 **이 버튼을 누르는 순간부터 과금된다.** g4dn.xlarge 온디맨드는 시간당 약
$0.5\~0.8이고, 켜 둔 채 두면 **월 $400\~600**이다.

### 5-4. 끄는 법 — 지금 외워 둔다

**EC2 → 인스턴스 → 선택 → 인스턴스 상태**

- **인스턴스 중지** — 시간당 요금이 멈춘다. EBS(월 $15 내외)와 모델 캐시는
  남으므로 다시 켜면 바로 쓸 수 있다. **퍼블릭 IP는 바뀐다.**
- **인스턴스 종료** — 완전히 지운다. EBS도 사라진다(모델 캐시 포함).

**검증 단계에서는 쓸 때만 켠다.** 하루 2시간 쓰면 월 $30\~50 수준이다.

---

## 6. 접속 확인

퍼블릭 IP는 인스턴스 상세 화면의 **퍼블릭 IPv4 주소**에 있다.

```bash
ssh -i ~/.ssh/supersub-ai.pem ubuntu@<퍼블릭-IP>
```

접속되면 안에서:

```bash
nvidia-smi          # Tesla T4, 15360MiB
df -h /             # 여유 60GB 이상
free -g             # 총 15GB 내외
aws sts get-caller-identity   # 역할을 붙였으면 계정이 나온다
aws s3 ls s3://supersub-ai-070605553723/
```

`aws sts get-caller-identity`가 자격증명 없다고 하면 인스턴스 프로파일이 안
붙은 것이다. 인스턴스를 다시 만들 필요는 없다 — **작업 → 보안 → IAM 역할 수정**
으로 나중에 붙일 수 있다. (VPC와 달리 역할은 나중에 바꿀 수 있다.)

---

## 7. 여기서부터는 [`README.md`](README.md)

콘솔에서 할 일은 끝났다. 남은 것은 전부 EC2 안에서 SSH로 한다.

| 다음 | 무엇 |
|---|---|
| [4장](README.md#4-ec2-초기-세팅) | 저장소 clone(ho 브랜치), uv, 의존성 |
| [5장](README.md#5-exaone-40-12b--s3--vllm) | EXAONE 다운로드 → S3 업로드 → vLLM 기동, **5-4 포즈 모델 미리 받기** |
| [6장](README.md#6-에이전트-실행--s3-영상--분석--s3-리포트) | 분석 한 바퀴 |
| [7장](README.md#7-수동-배포-운영-git-pull-origin-ho) | `git pull origin ho` 배포 |
| [8장](README.md#8-트러블슈팅) | 트러블슈팅 |

**5장의 모델 업로드에 주의한다.** 2-1의 IAM 정책은 `models/`에 **쓰기를 주지
않았다.** EC2에서 `aws s3 sync`로 올리려면 정책에 `models/*` PutObject를
한시적으로 더하거나, **콘솔에서 사람이 직접 업로드**해야 한다. 후자가 안전하다 —
모델은 한 번 올리면 끝이고, 인스턴스에 쓰기 권한을 상시로 주는 것보다 낫다.

---

## 정리(삭제)할 때 — 역순으로

의존 관계 때문에 순서를 지켜야 한다.

1. **EC2 인스턴스 종료** (가장 큰 비용)
2. VPC 엔드포인트 삭제
3. 보안 그룹 삭제
4. 인터넷 게이트웨이 분리 → 삭제
5. 서브넷 → 라우팅 테이블 → VPC 삭제
6. S3 버킷 비우기 → 삭제 (**버저닝을 켰으므로 이전 버전까지 지워야 비워진다**)
7. IAM 역할·정책 삭제
8. 키 페어 삭제

**1번만 해도 비용의 대부분이 멈춘다.** 나머지는 급하지 않다 — VPC 관련은
무료이고 S3는 용량만큼만 나온다.
