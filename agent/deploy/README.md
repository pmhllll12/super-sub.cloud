# AWS 배포 런북 — 독립 GPU 환경에 분석 에이전트 올리기

AI 전용 VPC에 S3 + EC2(g4dn.xlarge)를 세우고, EXAONE 4.0 1.2B를 vLLM으로 띄운 뒤
S3 영상을 분석해 리포트를 S3로 되돌려 놓는 데까지의 순서다.

각 단계는 **확인 명령으로 끝난다.** 그게 없으면 실패가 다음 단계에서 다른
증상으로 나타난다.

> **CLI 자격증명이 없다면** 1\~3장(S3·IAM·VPC·EC2 생성)은
> [`README-console.md`](README-console.md)에 콘솔 클릭 순서로 옮겨 두었다.
> **4장부터는 EC2 안에서 SSH로 하는 작업이라 두 경로가 같다** — 여기로 돌아온다.

> ### 격리 수준 — "완전히 분리"가 아니다
>
> 처음 계획은 **AI 전용 계정**이었지만, 실제로 쓰는 계정(`0706-0555-3723`,
> IAM 사용자 `ho`)이 **팀 프로젝트와 같은 계정**이다. 계정 경계는 공유되므로
> 아래는 공유된다.
>
> | 공유되는 것 | 분리되는 것 |
> |---|---|
> | 결제·비용 (태그로 구분은 된다) | 네트워크 — 전용 VPC (3-1) |
> | 서비스 할당량 (G 인스턴스 vCPU 등) | EC2의 데이터 접근 — IAM 역할이 AI 버킷 세 접두사만 허용 (2-A) |
> | 루트·관리자 권한의 영향 범위 | 스토리지 — 전용 버킷 |
>
> **실질적으로 중요한 것은 확보된다.** EC2 인스턴스는 팀 데이터를 읽지 못하고
> (`videos/`엔 쓰지도 못한다), 네트워크도 갈라져 있다. 남는 위험은 계정 단위
> 사고(관리자 실수, 할당량 소진, 결제 정지)가 양쪽에 함께 미친다는 것이다.
> 상용 단계에서 계정을 가르려면 그때 옮겨야 하고, **VPC는 생성 후 바꿀 수 없어
> 인스턴스를 다시 만들어야 한다** — 지금 전용 VPC로 시작해 두면 그 이사가 쉬워진다.

---

## 0. 시작 전 — 이 배포가 건드리는 것 넷

넘어가도 되지만, 나중에 되돌리기 비싼 것들이라 먼저 적는다.

### (1) EXAONE 4.0은 비상업(NC) 라이선스다 — 미결 1번

`EXAONE AI Model License Agreement 1.2 - NC`다. 개발·검증 목적의 EC2 구동은
문제없지만, **이 인스턴스가 외부 사용자에게 서비스를 제공하는 순간** 미결 1번이
열린 채로 상용 경로에 들어간다. 지금 단계(내부 검증)에서는 진행하되, 서비스
오픈 전에 결론이 필요하다.

### (2) `yolo11n.pt`는 서비스 경로가 쓰지 않는다

유일한 사용처가 `scripts/track_overlay.py`(검수용 추적 오버레이 영상)다.
분석 파이프라인의 비전 인식은 **RT-DETR(사람 검출) + ViTPose(포즈)** 이고 둘 다
Apache-2.0이다. `pyproject.toml:42`에 이유가 적혀 있다 — **ultralytics는
AGPL-3.0**이라 링크한 채 네트워크 서비스를 제공하면 소스 공개 의무가 생긴다.

그래서 이 런북은 **EC2에 `--extra tracking`을 설치하지 않는다.** 분석 품질에는
영향이 없다(서비스 경로가 원래 YOLO를 안 쓴다). 오버레이가 필요하면 로컬에서
뽑는다 — 로컬 `.venv`에는 이미 설치돼 있고 실제로 동작한다(2026-09-02 확인:
1080p 46프레임 7초, 4K 92프레임 25초).

**가중치 파일도 EC2로 가지 않는다.** `yolo11n.pt`는 `.gitignore`의 `agent/*.pt`에
걸려 있어 저장소에 없다 — `git pull`로 따라오지 않는다. 그래서 EC2에서
`track_overlay.py`를 실행하면 `from ultralytics import YOLO`에서 멈춘다.
막아 둔 것이 아니라 **설치를 안 해서 안 되는 것**이므로, 누가
`uv sync --extra tracking`을 치면 그때부터는 된다(ultralytics가 가중치를 자동으로
내려받는다). 미결 항목 「AWS 배포가 라이선스 두 건을 상용 경로 앞에 세웠다」가
이 점을 다룬다.

### (3) T4는 bfloat16을 못 쓴다

T4는 Turing(SM 7.5)이고 bf16 네이티브 지원이 없다. vLLM은 compute capability
8.0 미만에서 `--dtype bfloat16`을 **명시적으로 거부한다.** `serve_vllm.sh`가
`--dtype float16`으로 고정해 둔 이유다. (`judge.py`의 로컬 경로가 bf16인 것은
개발 GPU 기준이고, EC2에서는 그 경로를 안 탄다.)

### (4) g4dn.xlarge의 호스트 RAM은 16GB뿐이다 — 미결 9번

미결 9번이 "4K 입력에서 host RAM이 먼저 터진다"이다. `pose.py`가 300프레임으로
막고 있지만 4K 300장은 그것만으로 수 GB다. **4K 원본을 그대로 넣지 말고**
업로드 전에 1080p로 줄이거나, 터지면 인스턴스를 g4dn.2xlarge(32GB)로 올린다.

### 포트 배치

`api.py`가 이미 8000을 문서화하고 있어 vLLM과 충돌한다. 이렇게 나눈다.

| 포트 | 무엇 | 노출 |
|---|---|---|
| 8000 | vLLM (OpenAI 호환) | **127.0.0.1 전용 — 보안 그룹에 열지 않는다** |
| 8080 | `api.py` (필요할 때만) | 팀 IP만 |
| 22 | SSH | 내 IP만 |

**vLLM은 인증이 없다.** 0.0.0.0에 묶고 보안 그룹을 열면 그 순간 누구나 GPU를
쓸 수 있다. 루프백에 두고, 밖에서 봐야 하면 SSH 터널을 쓴다.

---

## 1. S3 버킷 생성 및 보안 설정

버킷 하나에 접두사로 용도를 나눈다. 버킷을 셋으로 쪼개면 IAM 정책도 셋이 된다.

```
s3://supersub-ai/
├── videos/      # 원본 영상 (입력)
├── models/      # EXAONE 가중치
└── reports/     # 분석 리포트 (출력)
```

S3 이름은 **전 세계에서 유일**해야 한다. `supersub-ai`가 비어 있어 그대로 썼다
(2026-09-02 생성). 다른 계정에서 다시 만들 때 이미 쓰이고 있으면 계정번호를
뒤에 붙이고, **그 이름을 IAM 정책·vllm.env·분석 명령 인자에 모두 반영**한다.
리전은 서울(`ap-northeast-2`)을
가정한다 — **EC2와 반드시 같은 리전**이어야 한다(리전이 다르면 영상마다 리전 간
전송료가 붙는다).

```bash
export AWS_REGION=ap-northeast-2
export ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export BUCKET=supersub-ai        # 2026-09-02 콘솔에서 이 이름으로 생성됨

aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION" \
  --create-bucket-configuration LocationConstraint="$AWS_REGION"
```

### 보안 설정 넷 — 순서대로

```bash
# (1) 퍼블릭 액세스 전면 차단. 기본값이지만 명시해 둔다.
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# (2) 기본 암호화(SSE-S3) + 버킷 키 — 요청당 KMS 비용 없이 암호화된다.
aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration '{
    "Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},
              "BucketKeyEnabled":true}]}'

# (3) 버저닝 — 리포트를 덮어써도 이전 것이 남는다.
aws s3api put-bucket-versioning --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

# (4) 평문 HTTP 거부.
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "{
  \"Version\":\"2012-10-17\",
  \"Statement\":[{
    \"Sid\":\"DenyInsecureTransport\",
    \"Effect\":\"Deny\",\"Principal\":\"*\",\"Action\":\"s3:*\",
    \"Resource\":[\"arn:aws:s3:::$BUCKET\",\"arn:aws:s3:::$BUCKET/*\"],
    \"Condition\":{\"Bool\":{\"aws:SecureTransport\":\"false\"}}}]}"
```

**확인:**
```bash
aws s3api get-public-access-block --bucket "$BUCKET" \
  --query PublicAccessBlockConfiguration
# 네 값이 모두 true여야 한다.
```

### 수명주기 (선택)

원본 영상은 분석이 끝나면 다시 안 읽는다. 90일 뒤 저비용 계층으로 내린다.

```bash
aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" \
  --lifecycle-configuration '{"Rules":[{
    "ID":"videos-to-ia","Status":"Enabled",
    "Filter":{"Prefix":"videos/"},
    "Transitions":[{"Days":90,"StorageClass":"STANDARD_IA"}]}]}'
```

`models/`에는 걸지 않는다 — 인스턴스를 새로 띄울 때마다 읽는다.

---

## 2. IAM — EC2가 S3에 접근하는 방법

요청하신 `aws configure` 방식도 아래 2-B에 적었지만, **2-A(인스턴스 역할)를
권합니다.** 이유는 하나다: `aws configure`는 장기 액세스 키를 EC2 디스크
(`~/.aws/credentials`)에 평문으로 남기고, 그 디스크는 스냅샷·AMI·백업에 그대로
딸려 나간다. 역할은 키가 없고 자동으로 교체된다.

### 2-A. 인스턴스 프로파일 (권장)

```bash
# 신뢰 정책 — EC2만 이 역할을 맡을 수 있다.
cat > /tmp/trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
 "Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF

aws iam create-role --role-name supersub-ai-ec2 \
  --assume-role-policy-document file:///tmp/trust.json

# 최소 권한 — 이 버킷의 세 접두사만. 다른 팀 버킷은 보이지도 않는다.
cat > /tmp/policy.json <<EOF
{"Version":"2012-10-17","Statement":[
 {"Sid":"ListOnlyOurPrefixes","Effect":"Allow","Action":"s3:ListBucket",
  "Resource":"arn:aws:s3:::$BUCKET",
  "Condition":{"StringLike":{"s3:prefix":["videos/*","models/*","reports/*"]}}},
 {"Sid":"ReadInputsAndModel","Effect":"Allow","Action":"s3:GetObject",
  "Resource":["arn:aws:s3:::$BUCKET/videos/*","arn:aws:s3:::$BUCKET/models/*"]},
 {"Sid":"WriteReports","Effect":"Allow","Action":["s3:PutObject"],
  "Resource":"arn:aws:s3:::$BUCKET/reports/*"}]}
EOF

aws iam put-role-policy --role-name supersub-ai-ec2 \
  --policy-name supersub-s3 --policy-document file:///tmp/policy.json

aws iam create-instance-profile --instance-profile-name supersub-ai-ec2
aws iam add-role-to-instance-profile \
  --instance-profile-name supersub-ai-ec2 --role-name supersub-ai-ec2
```

`videos/`에 쓰기 권한이 없는 게 의도다 — 영상 업로드는 사람이 하고, EC2는
읽기만 한다. EC2가 털려도 원본을 지우지 못한다.

### 2-B. `aws configure` (요청하신 방식)

역할을 못 쓰는 상황이면 IAM 사용자를 만들어 같은 정책을 붙이고 키로 설정한다.

```bash
aws iam create-user --user-name supersub-ai-agent
aws iam put-user-policy --user-name supersub-ai-agent \
  --policy-name supersub-s3 --policy-document file:///tmp/policy.json
aws iam create-access-key --user-name supersub-ai-agent   # 이 출력은 한 번만 보인다
```

EC2 안에서:
```bash
aws configure
#   AWS Access Key ID     : (위 출력)
#   AWS Secret Access Key : (위 출력)
#   Default region name   : ap-northeast-2
#   Default output format : json
chmod 600 ~/.aws/credentials
```

이 경로를 쓴다면 **키를 90일마다 교체**하고, 인스턴스를 AMI로 굽기 전에
`~/.aws/credentials`를 지운다.

**확인 (어느 방식이든 EC2 안에서):**
```bash
aws sts get-caller-identity
# Arn 이 assumed-role/supersub-ai-ec2/i-... 이면 역할이 붙은 것이다

# 🔴 **접두사를 붙여서** 나열한다. `aws s3 ls s3://$BUCKET/` (루트)는
# 이 정책에서 **항상 거부된다** — ListBucket 에 s3:prefix 조건을 걸어
# videos/·models/·reports/ 만 열어 두었기 때문이다. 거부가 정상이다.
aws s3 ls s3://$BUCKET/videos/

# 권한이 의도대로 좁혀졌는지 — 아래는 **실패해야 맞다.**
echo probe > /tmp/_probe.txt
aws s3 cp /tmp/_probe.txt s3://$BUCKET/reports/_probe.txt   # 성공해야 한다
aws s3 cp /tmp/_probe.txt s3://$BUCKET/videos/_probe.txt    # AccessDenied 가 정상
```

> `reports/` 에 남은 `_probe.txt` 는 EC2 에서 지울 수 없다 — 정책에
> `DeleteObject` 가 없다(그것도 의도다). 콘솔에서 지운다.

---

## 3. EC2 GPU 인스턴스 생성

### 3-1. 전용 VPC — **추가 비용 없음**

팀 계정을 공유해 쓰므로(계정 `0706-0555-3723`) 네트워크만이라도 갈라 둔다.
기본 VPC에 넣으면 팀 리소스와 같은 네트워크에 놓이고, 나중에 옮기려면
**인스턴스를 다시 만들어야 한다** — VPC는 생성 후 바꿀 수 없다.

돈 걱정은 하지 않아도 된다. **VPC·서브넷·라우팅 테이블·인터넷 게이트웨이·
보안 그룹은 전부 무료다.** 요금이 붙는 것은 **NAT 게이트웨이**(월 $45 안팎)인데
여기서는 쓰지 않는다 — 인스턴스를 퍼블릭 서브넷에 두고 IGW로 직접 나간다.
퍼블릭 IPv4 주소 요금(월 $3.6 안팎)은 기본 VPC에서도 똑같이 내므로 차이가 아니다.

```bash
# CIDR은 기본 VPC(172.31.0.0/16)와 겹치지 않게 잡는다.
export VPC=$(aws ec2 create-vpc --cidr-block 10.20.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=supersub-ai-vpc},{Key=Project,Value=supersub-agent}]' \
  --query Vpc.VpcId --output text)

# DNS 이름이 켜져 있어야 인스턴스가 퍼블릭 DNS를 받고 HF·apt를 해석한다.
aws ec2 modify-vpc-attribute --vpc-id "$VPC" --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id "$VPC" --enable-dns-hostnames

export SUBNET=$(aws ec2 create-subnet --vpc-id "$VPC" \
  --cidr-block 10.20.1.0/24 --availability-zone ${AWS_REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=supersub-ai-public}]' \
  --query Subnet.SubnetId --output text)
aws ec2 modify-subnet-attribute --subnet-id "$SUBNET" --map-public-ip-on-launch

# 인터넷 게이트웨이 — 무료다. 이게 없으면 모델도 apt도 못 받는다.
export IGW=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=supersub-ai-igw}]' \
  --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway --vpc-id "$VPC" --internet-gateway-id "$IGW"

export RTB=$(aws ec2 create-route-table --vpc-id "$VPC" \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=supersub-ai-rtb}]' \
  --query RouteTable.RouteTableId --output text)
aws ec2 create-route --route-table-id "$RTB" \
  --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW"
aws ec2 associate-route-table --route-table-id "$RTB" --subnet-id "$SUBNET"

# S3 게이트웨이 엔드포인트 — **무료이고 켜 두는 편이 낫다.**
# 영상·모델 트래픽이 인터넷을 타지 않고 AWS 내부로 간다(빠르고, 나중에
# 이그레스를 막는 구성으로 갈 때 S3만은 계속 된다).
aws ec2 create-vpc-endpoint --vpc-id "$VPC" \
  --service-name com.amazonaws.${AWS_REGION}.s3 \
  --route-table-ids "$RTB"
```

**확인:**
```bash
aws ec2 describe-vpcs --vpc-ids "$VPC" --query 'Vpcs[0].[VpcId,CidrBlock,State]' --output text
aws ec2 describe-route-tables --route-table-ids "$RTB" \
  --query 'RouteTables[0].Routes[].[DestinationCidrBlock,GatewayId]' --output text
# 0.0.0.0/0 → igw-... 와 S3 prefix list → vpce-... 두 줄이 보여야 한다
```

> **여기서 만든 것 중 유료는 없다.** 나중에 정리할 때는 EC2 → 엔드포인트 →
> IGW → 서브넷 → VPC 순서로 지운다(의존 때문에 역순으로는 안 지워진다).

### 3-2. 보안 그룹

```bash
export MY_IP=$(curl -s https://checkip.amazonaws.com)

export SG=$(aws ec2 create-security-group --group-name supersub-ai-sg \
  --description "Super-Sub AI agent (isolated)" --vpc-id "$VPC" \
  --query GroupId --output text)

# SSH — 내 IP만.
aws ec2 authorize-security-group-ingress --group-id "$SG" \
  --protocol tcp --port 22 --cidr "$MY_IP/32"

# 8080(api.py)은 **필요할 때만** 연다. 지금은 열지 않는다.
# aws ec2 authorize-security-group-ingress --group-id "$SG" \
#   --protocol tcp --port 8080 --cidr "$MY_IP/32"
```

**8000(vLLM)은 열지 않는다.** 루프백에 묶여 있고, 밖에서 봐야 하면 터널을 쓴다:

```bash
ssh -i ~/.ssh/supersub-ai.pem -L 8000:127.0.0.1:8000 ubuntu@<EC2-IP>
# 이제 로컬 http://127.0.0.1:8000/v1/models 가 EC2의 vLLM이다
```

### 3-3. AMI 고르기

**Deep Learning OSS Nvidia Driver AMI (Ubuntu 22.04)** — NVIDIA 드라이버·CUDA가
미리 깔려 있다. AMI ID는 리전·시점마다 바뀌므로 이름으로 찾는다:

```bash
aws ec2 describe-images --owners amazon \
  --filters 'Name=name,Values=Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Ubuntu 22.04*' \
  --query 'reverse(sort_by(Images,&CreationDate))[:3].[ImageId,Name]' --output table
```

가장 최근 것의 `ImageId`를 쓴다.

### 3-4. 인스턴스 실행

```bash
aws ec2 create-key-pair --key-name supersub-ai \
  --query KeyMaterial --output text > ~/.ssh/supersub-ai.pem
chmod 400 ~/.ssh/supersub-ai.pem

aws ec2 run-instances \
  --image-id <위에서 찾은 AMI> \
  --instance-type g4dn.xlarge \
  --key-name supersub-ai \
  --security-group-ids "$SG" \
  --subnet-id "$SUBNET" \
  --associate-public-ip-address \
  --iam-instance-profile Name=supersub-ai-ec2 \
  --block-device-mappings '[{"DeviceName":"/dev/sda1",
     "Ebs":{"VolumeSize":150,"VolumeType":"gp3","DeleteOnTermination":true,
            "Encrypted":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=supersub-ai},{Key=Project,Value=supersub-agent}]'
```

**EBS를 150GB로 잡은 이유.** DLAMI 자체가 이미 50\~90GB를 쓴다. 여기에
HuggingFace 캐시(EXAONE + RT-DETR + ViTPose)와 임시 영상이 더해진다. 100GB로
시작하면 모델 두어 개 받다가 꽉 찬다. gp3는 GB당 과금이라 50GB 더 잡아도 월
몇 달러 차이다.

**확인 (SSH 접속 후):**
```bash
nvidia-smi          # Tesla T4, 15360MiB 가 보여야 한다
df -h /             # 여유 60GB 이상
free -g             # 총 15GB 내외 — 미결 9번(4K host RAM)을 기억할 것
```

### 3-5. 비용 — 끄는 습관을 먼저 만든다

**서울 기준 단가** (2026-09-03 확인).

| 항목 | 단가 |
|---|---|
| g4dn.xlarge 온디맨드 | **$0.647/시간** |
| g4dn.xlarge **스팟** | **$0.2219/시간** (66% 싸다) |
| gp3 150GB | $0.0912/GB·월 → **$13.7/월** (인스턴스가 꺼져 있어도 나간다) |
| 퍼블릭 IPv4 | $0.005/시간 |
| VPC·서브넷·IGW·보안그룹·S3 엔드포인트 | **$0** |

**시간이 전부다.** 켜 둔 시간에 거의 정비례한다.

| 쓰는 방식 | 월 시간 | 합계 |
|---|---:|---:|
| 하루 2시간 | 60h | 약 $53 |
| 평일 10시간 | 220h | 약 $157 |
| **켜 두고 방치** | 730h | **약 $490** |
| 중지만 해 둠 | 0h | 약 $14 (EBS) |

**방치와 하루 2시간이 9배 차이다.** 이 배포에서 무서운 숫자는 이것 하나뿐이다.

```bash
export IID=<인스턴스 ID>
aws ec2 stop-instances  --instance-ids "$IID"   # 중지 — EBS 요금만 남는다
aws ec2 start-instances --instance-ids "$IID"   # 재개 (퍼블릭 IP는 바뀐다)
```

중지해도 EBS와 모델 캐시는 남으므로 다시 켜면 바로 쓸 수 있다. 퍼블릭 IP
고정이 필요하면 Elastic IP를 붙이되, **미사용 EIP는 따로 과금**되므로
인스턴스를 없앨 때 같이 해제한다.

> **디스크를 줄여 아끼려 하지 않는다.** 우리가 쓰는 용량은 실측 약 9.4GB다
> (`.venv` 6.5GB + HF 캐시 2.9GB — EXAONE 2.4GB·ViTPose 328MB·RT-DETR 165MB).
> 150 → 100GB로 줄여도 **월 $4.6**이고 전체의 3%다. 반대로 디스크가 차서
> 모델 받다 멈추면 그걸 고치는 GPU 시간이 아낀 돈을 금방 넘는다.
> gp3는 나중에 **키울 수는 있어도 줄일 수 없다.**

### 3-6. 자동 종료 — 끄는 것을 잊어도 꺼지게

위 표에서 보듯 **끄는 걸 잊는 것이 유일한 큰 위험**이다. 금요일 저녁에 한 번
안 끄면 월요일까지 61시간이 붙어 **$40**이다.

보통 쓰는 자동 종료(CloudWatch 알람, EC2 Instance Scheduler, Lambda)는 전부
IAM 권한이 필요한데 `ho`는 IAM이 전면 차단이다. **인스턴스 안에서 스스로
poweroff 하는 방식**은 AWS 자격증명이 하나도 없어도 되므로 지금 되는 유일한
방법이고, EBS 기반 인스턴스는 안에서 halt 하면 **stop 상태로 떨어져 과금이
멈춘다.**

🔴 **설치 전에 종료 동작을 확인한다.**

**EC2 → 인스턴스 선택 → 작업 → 인스턴스 설정 → 종료 동작 변경**

여기가 **`중지(stop)`** 여야 한다. `종료(terminate)`면 자동 종료가 인스턴스와
EBS를 **지운다.** 콘솔 기본값은 `중지`지만 기본값을 믿고 돌리지 않는다 —
인스턴스 안에서는 이 값을 읽을 방법이 없다(IMDS가 노출하지 않고,
`ec2:DescribeInstanceAttribute`는 자격증명이 필요한데 역할이 없다).

```bash
cd ~/super-sub.cloud
sudo ./agent/deploy/install_autostop.sh --shutdown-behavior-verified
```

확인 플래그 없이 실행하면 설치를 거부하고 위 콘솔 경로를 알려 준다.

**판정 기준** (`/etc/supersub/autostop.conf`에서 바꾼다).

| 상황 | 스크립트 기본값 | 🔴 `supersub-ai`에 **깔린 값** |
|---|---|---|
| 접속도 작업도 없음 | 30분 | **90분** |
| 접속은 있으나 작업 없음 (터미널 켜 두고 퇴근) | 120분 | **240분** |
| 무엇을 하든 (최후의 안전장치) | 12시간 | **18시간** |

🔴 **두 값이 다르다.** 2026-09-04에 `supersub-ai`의
`/etc/supersub/autostop.conf`만 올렸고 **스크립트 기본값(`autostop.sh`)과
`autostop.conf.example`은 그대로 두었다** — 그 둘은 "기본값이 무엇인가"를
설명하는 자리라 배포 한 대의 사정으로 바꾸면 다음 배포가 그 값을 물려받는다.
되돌리려면 인스턴스에서 한 줄이다(백업이 `autostop.conf.bak.20260904`에 있다):

```bash
sudo sed -i -e 's/^IDLE_MINUTES=90$/IDLE_MINUTES=30/' \
            -e 's/^SSH_IDLE_MINUTES=240$/SSH_IDLE_MINUTES=120/' \
            -e 's/^MAX_UPTIME_HOURS=18$/MAX_UPTIME_HOURS=12/' /etc/supersub/autostop.conf
```

**최악의 경우 비용이 늘었다** — 잊고 두면 12시간 $7.8에서 **18시간 $11.6**이
된다(온디맨드 $0.647/시간). 오래 걸리는 작업 앞에는 여전히 `supersub-hold`가
맞는 도구다. 이쪽은 만료가 있고 저쪽은 없다.

"작업 중"은 **GPU 사용률 10% 초과** 또는 **분석 프로세스 실행 중**이다.

> **GPU 메모리는 쓰지 않는다.** vLLM이 상주하며 VRAM을 미리 잡기 때문에
> (`vllm.env`의 `SUPERSUB_GPU_FRACTION=0.35`), 메모리로 보면 vLLM이 떠 있는 한
> 영원히 "바쁨"이 되어 자동 종료가 무력해진다. 사용률은 요청이 없으면 0으로
> 떨어지므로 그쪽을 본다.
>
> **프로세스 패턴은 명령줄 맨 앞을 고정해 두었다.** `pgrep -f`는 명령줄
> 어디에나 그 문자열이 있으면 걸려서, 파일 이름만 적으면 `vim analyze.py`도
> "작업 중"이 된다 — 편집기를 열어 둔 채 자리를 뜨면 영영 안 꺼진다.
> 패턴을 고칠 때 이 성질을 깨지 않는다.

오래 걸리는 작업 앞에는 **보류**를 건다. 타이머를 `systemctl stop` 하지 않는다 —
다시 켜는 것을 잊으면 자동 종료가 없는 것과 같아진다. 보류는 만료가 있다.

```bash
sudo supersub-hold 4h     # 4시간 보류
sudo supersub-hold        # 남은 시간 확인
sudo supersub-hold off    # 즉시 해제

journalctl -u supersub-autostop -n 30 --no-pager   # 판정 기록
```

---

## 4. EC2 초기 세팅

```bash
ssh -i ~/.ssh/supersub-ai.pem ubuntu@<EC2-IP>

# --- 저장소 (ho 브랜치) ---
sudo apt-get update && sudo apt-get install -y git ffmpeg
git clone -b ho https://github.com/pmhllll12/super-sub.cloud.git ~/super-sub.cloud
cd ~/super-sub.cloud/agent

# --- uv + 의존성 ---
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv sync --extra aws          # ← tracking(ultralytics/AGPL)은 넣지 않는다. 0절 (2) 참고

# --- 확인 ---
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# True Tesla T4
uv run python -m pytest -q   # GPU 없이 도는 테스트들 — 전부 통과해야 한다
```

> `pyproject.toml`이 torch를 cu126 인덱스로 고정하고 있다(WSL 드라이버 사정).
> DLAMI의 드라이버가 더 최신이라 cu126 휠은 정상 동작한다. `torch.cuda.is_available()`이
> False면 여기서 멈추고 드라이버/휠 조합부터 맞춘다 — 뒤 단계가 전부 이것에 걸린다.

---

## 5. EXAONE 4.0 1.2B → S3 → vLLM

### 5-1. 모델을 받아 S3에 올린다 (최초 1회)

EC2에서 받아서 올린다. 로컬에서 올리면 집 회선으로 5GB를 올려야 한다.

```bash
cd ~/super-sub.cloud/agent
uv pip install "huggingface_hub[cli]"   # ← uv run pip 이 아니다. 아래 참고

uv run hf download LGAI-EXAONE/EXAONE-4.0-1.2B \
  --local-dir /opt/supersub/models/exaone-4.0-1.2b

# 안전텐서·설정·토크나이저만 올린다. .cache 같은 부산물은 뺀다.
aws s3 sync /opt/supersub/models/exaone-4.0-1.2b \
  s3://$BUCKET/models/exaone-4.0-1.2b \
  --exclude ".cache/*" --exclude "*.lock"
```

`/opt/supersub`에 권한이 없으면 먼저:
`sudo mkdir -p /opt/supersub/models && sudo chown -R ubuntu:ubuntu /opt/supersub`

> 🔴 **`uv run pip` 이 아니라 `uv pip` 이다.** uv가 만든 venv에는 pip이 없어서
> `uv run pip` 은 **시스템 pip으로 떨어지고**, Ubuntu 26.04(DLAMI 2026-09)에서는
> PEP 668이 이를 거부한다(`externally-managed-environment`). 2026-09-03에 실제로
> 여기서 멈췄다 — `set -e` 스크립트 안이면 뒤 단계가 통째로 건너뛰어지므로
> 다운로드가 된 줄 알고 넘어가기 쉽다.

**확인:**
```bash
aws s3 ls s3://$BUCKET/models/exaone-4.0-1.2b/
# config.json, tokenizer_config.json, model*.safetensors 가 보여야 한다
```

> **왜 S3에 두는가.** vLLM은 `s3://`를 직접 읽지 못한다 — `sync_model.sh`가
> 기동 전에 로컬로 받아 놓고 그 경로로 띄운다. 이렇게 해 두면 인스턴스를 지웠다
> 새로 만들어도 HuggingFace를 다시 안 거치고(수 분 절약, 레이트리밋 없음)
> **모든 인스턴스가 똑같은 가중치**를 쓴다.

### 5-2. vLLM 설치 — **에이전트 venv 가 아니라 전용 venv 에**

🔴 **`agent/` 안에서 `uv pip install vllm` 을 하지 않는다.** vLLM 휠은 자기가
빌드된 torch 에만 맞는 C 확장을 들고 오는데, `pyproject.toml` 은 torch 를
cu126 · `<2.9` 로 고정한다(WSL 개발기 드라이버 사정). 같은 venv 에 넣으면
둘 중 하나가 반드시 깨진다 — 2026-09-03 에 `import vllm` 이
`undefined symbol: torch_list_size` 로 죽었고, 되돌리려고 `uv sync` 를 돌렸더니
정리 과정에서 torch 가 `libcusparseLt.so.0` 을 잃어 **에이전트까지 못 쓰게
됐다**(`rm -rf .venv && uv sync --extra aws` 로 복구).

vLLM 서버는 별도 프로세스라 venv 를 나눠도 아무 손해가 없다.

```bash
uv venv /opt/supersub/vllm-venv --python 3.12
VIRTUAL_ENV=/opt/supersub/vllm-venv uv pip install vllm

# EXAONE 4.0 지원 여부를 여기서 확인한다. 아키텍처가 Exaone4ForCausalLM이라
# 오래된 vLLM은 "not supported"로 죽는다.
/opt/supersub/vllm-venv/bin/python -c "
import vllm, torch
print(vllm.__version__, torch.__version__, torch.cuda.is_available())
from vllm.model_executor.models.registry import ModelRegistry
print([a for a in ModelRegistry.get_supported_archs() if 'xaone' in a.lower()])"
# Exaone4ForCausalLM 이 나와야 한다. 없으면 vLLM을 최신으로 올린다.
```

2026-09-03 기준 이 조합은 **vllm 0.28.0 / torch 2.13.0+cu130** 이고 T4 에서
`cuda True` 다. 전용 venv 라 cu130 을 그대로 써도 된다 — cu126 고정은 WSL
개발기 사정이고 DLAMI 드라이버는 그보다 최신이다. `serve_vllm.sh` 가
`SUPERSUB_VLLM_BIN`(기본 `/opt/supersub/vllm-venv/bin/vllm`)으로 이 venv 를
가리킨다.

### 5-3. 서버 기동

```bash
sudo mkdir -p /etc/supersub
sudo cp deploy/vllm.env.example /etc/supersub/vllm.env
sudo chmod 600 /etc/supersub/vllm.env

# IAM 역할이 없으면(README-console 2-C) S3를 건너뛴다 — 5-1에서 HF로 받은
# /opt/supersub/models/exaone-4.0-1.2b 를 그대로 쓴다.
sudo sed -i 's|^SUPERSUB_MODEL_S3=.*|SUPERSUB_MODEL_S3=|' /etc/supersub/vllm.env

sudo cp deploy/supersub-vllm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now supersub-vllm
```

> 예시 파일에 버킷 이름(`supersub-ai`)이 이미 들어 있다. 다른 버킷을 쓸 때만
> `SUPERSUB_MODEL_S3` 줄을 고친다.

**확인:**
```bash
curl -s http://127.0.0.1:8000/v1/models | python3 -m json.tool
# id 가 "LGAI-EXAONE/EXAONE-4.0-1.2B" 여야 한다 (judge.py의 MODELS와 같은 값)

nvidia-smi --query-gpu=memory.used,memory.total --format=csv
# 5000MiB 내외 / 15360MiB — 나머지가 포즈 모델 몫이다
```

GPU 사용량이 13GB 이상이면 `SUPERSUB_GPU_FRACTION`이 안 먹은 것이다. 그대로
두면 다음 단계의 포즈 추출이 OOM으로 죽는다.

**한 문장 생성까지 확인:**
```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' -d '{
    "model":"LGAI-EXAONE/EXAONE-4.0-1.2B",
    "messages":[{"role":"user","content":"한 문장으로 자기소개 해줘."}],
    "max_tokens":64,"temperature":0}' | python3 -m json.tool
```

### 5-4. 포즈 모델 미리 받기

**EXAONE만 챙기면 절반이다.** 서비스 경로의 비전 인식은 RT-DETR + ViTPose이고,
`pose.py`가 이 둘을 **실행 시점에 HuggingFace에서** 내려받는다
(`from_pretrained`). 그냥 두면 첫 분석이 S3에서 영상을 받은 **다음에** 모델을
받으러 나간다 — 이그레스가 막혀 있거나 HF가 레이트리밋을 걸면 거기서 실패하고,
그때까지 쓴 시간이 버려진다.

```bash
cd ~/super-sub.cloud/agent
uv run python -c "
from transformers import AutoProcessor, RTDetrForObjectDetection, VitPoseForPoseEstimation
from supersub_agent.pose import PERSON_DETECTOR, POSE_MODEL
for name, cls in ((PERSON_DETECTOR, RTDetrForObjectDetection), (POSE_MODEL, VitPoseForPoseEstimation)):
    AutoProcessor.from_pretrained(name); cls.from_pretrained(name)
    print('받음:', name)
"
```

**확인:**
```bash
du -sh ~/.cache/huggingface/hub/*    # rtdetr, vitpose 두 항목이 보여야 한다
```

EXAONE과 달리 S3에 두지 않는 이유는 **바뀌지 않는 공개 가중치**라서다. EXAONE은
vLLM이 매 기동마다 읽어야 하고 인스턴스를 새로 만들 때마다 필요하지만, 이 둘은
HF 캐시에 한 번 들어가면 끝이다. 이그레스를 아예 막는 구성으로 갈 거라면 그때
같은 방식으로 S3에 올린다.

---

## 6. 에이전트 실행 — S3 영상 → 분석 → S3 리포트

### 6-1. 판정을 vLLM으로 보내는 스위치

```bash
echo 'export SUPERSUB_VLLM_URL=http://127.0.0.1:8000' >> ~/.bashrc
source ~/.bashrc
```

이 환경변수 하나가 백엔드를 정한다. **있으면 vLLM, 없으면 지금까지처럼
로컬 적재**다(`judge.py`). `api.py`도 `analyze.py`도 고칠 필요가 없고, 로컬
WSL 개발은 변수가 없으니 그대로다.

### 6-2. 파이프라인 한 바퀴

```bash
# 영상 올리기 (로컬에서)
aws s3 cp ./pitch01.mp4 s3://$BUCKET/videos/pitch01.mp4

# 분석 (EC2에서)
cd ~/super-sub.cloud/agent
uv run python scripts/analyze_s3.py s3://$BUCKET/videos/pitch01.mp4 \
  --rubric rubrics/baseball_pitching.yaml \
  --out s3://$BUCKET/reports \
  --side left
```

무슨 일이 일어나는가:

| | |
|---|---|
| 1 | `storage.download` — S3 원본을 임시 디렉터리로. 분석이 끝나면 지운다 |
| 2 | `pose.extract_keypoints` — RT-DETR로 사람 검출, ViTPose로 COCO-17 포즈. `target_fps=30`, 최대 300프레임 |
| 3 | `features.extract_features` — 정규화 → 임팩트 구간 분할 → 루브릭이 요구하는 지표 산출. `--side`는 루브릭의 `impact_limb`에만 적용된다 |
| 4 | `scoring.Criterion.grade_for` — **등급을 코드가 정한다.** 모델이 아니다 |
| 5 | `Judge` → vLLM `/v1/chat/completions` — 확정된 등급의 **근거 문장만** 생성. 항목 하나씩, `temperature=0`, `guided_json`으로 스키마 강제 |
| 6 | **미리보기 렌더링** — 원본을 다시 디코딩해 임팩트 스켈레톤 `impact.jpg`와 대상 추적 영상 `tracked.webm`을 만든다. 추가 추론이 없다(ViTPose 키포인트로 그리기만 한다) |
| 7 | `storage.upload_json` — `s3://버킷/reports/pitch01/<타임스탬프>.json` |

리포트에는 측정값·판정·타이밍과 함께 `code_version`(git 커밋)과
`judge_backend`가 들어간다. 수동 배포라 EC2 코드 시점이 리포트마다 다를 수
있어서다.

**확인:**
```bash
aws s3 ls --recursive s3://$BUCKET/reports/pitch01/
# <타임스탬프>.json  · <타임스탬프>/impact.jpg  · <타임스탬프>/tracked.webm

aws s3 cp s3://$BUCKET/reports/pitch01/<타임스탬프>.json - | python3 -m json.tool | head -40

# 그림을 눈으로 보려면 받아서 연다 (버킷은 퍼블릭이 아니다)
aws s3 cp s3://$BUCKET/reports/pitch01/<타임스탬프>/impact.jpg .
```

### 6-3. 툴 콜링에 대해

지금 `Judge`는 **툴 콜링을 하지 않는다.** 의도된 설계다 — `judge.py` 첫머리에
있듯 EXAONE 4.0 1.2B는 경계값 비교(141.7이 140\~165 안인지)를 **재현되게
틀렸고**, 그래서 등급 결정을 `scoring.Criterion.grade_for`(코드)로 옮겼다.
모델의 역할은 확정된 등급에 대한 설명 문장 생성 하나다.

vLLM은 OpenAI 호환이라 `tools`/`tool_choice`를 받을 수 있으므로 나중에 열 수는
있다. 다만 **지금 정확도 근거로는 1.2B에 판단을 되돌릴 이유가 없다.** 열려면
그 전에 "무엇을 모델이 정하게 할 것인가"를 정하고 근거를 남겨야 한다.

---

## 7. 수동 배포 운영 (`git pull origin ho`)

```
로컬(WSL) ──push──> GitHub(ho) ──pull──> EC2 ──restart──> vLLM
```

### 로컬에서

```bash
cd ~/projects/super-sub.cloud
git checkout ho
# ... 작업 ...
uv run --directory agent python -m pytest -q     # 푸시 전에 통과시킨다
git push origin ho
```

> 푸시가 403이면 `GITHUB_TOKEN` 환경변수를 빼고 다시 시도한다(이 저장소의
> 알려진 함정이다).

### EC2에서

```bash
cd ~/super-sub.cloud && ./agent/deploy/deploy.sh
```

`deploy.sh`가 하는 일: 작업 트리 청결 확인 → `git pull origin ho` →
`uv sync --extra aws` → `systemctl restart supersub-vllm` → **`/v1/models`가
응답할 때까지 기다렸다가 확인.** 마지막 단계가 핵심이다 — 재시작만 하고 끝내면
기동 실패를 다음 분석 때 알게 된다.

**EC2에서 코드를 직접 고치지 않는다.** `deploy.sh`가 더러운 작업 트리에서
멈추는 이유다. 고치면 다음 pull이 충돌하거나 덮어쓰고, 그때부터 어떤 코드가
도는지 아무도 모른다. 급하면 로컬에서 고쳐 푸시한다.

### 되돌리기

```bash
cd ~/super-sub.cloud
git log --oneline -10
git checkout <좋았던 커밋>          # detached HEAD — 임시 조치다
sudo systemctl restart supersub-vllm
# 원인을 고친 뒤에는 반드시 ho로 돌아온다: git checkout ho && git pull origin ho
```

---

## 8. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| `Bfloat16 is only supported on GPUs with compute capability of at least 8.0` | T4에 bf16을 요구했다 | `serve_vllm.sh`가 `--dtype float16`인지 확인. 직접 `vllm serve`를 친 것이면 그 옵션을 빼먹은 것 |
| `Judge.load()`가 `... 를 서빙하지 않는다` | `--served-model-name`이 `judge.py`의 `MODELS["1.2B"]`와 다르다 | `/etc/supersub/vllm.env`의 `SUPERSUB_SERVED_NAME`을 `LGAI-EXAONE/EXAONE-4.0-1.2B`로 |
| 포즈 추출에서 CUDA OOM | vLLM이 GPU를 너무 잡았다 | `nvidia-smi`로 확인 후 `SUPERSUB_GPU_FRACTION`을 0.30으로 낮추고 재시작 |
| vLLM 기동 중 OOM | KV 캐시 + CUDA 그래프 | `SUPERSUB_ENFORCE_EAGER=1` 확인, `SUPERSUB_MAX_MODEL_LEN`을 2048로 |
| 분석 중 프로세스가 조용히 죽음(OOMKilled) | **호스트 RAM**이지 GPU가 아니다. 미결 9번 | `dmesg | tail`로 확인. 4K 영상을 1080p로 줄이거나 g4dn.2xlarge로 |
| `vllm serve`가 `Exaone4ForCausalLM ... not supported` | vLLM이 오래됐다 | 5-2의 확인 명령을 돌리고 vLLM 업그레이드 |
| `botocore ... NoCredentialsError` | 인스턴스 프로파일이 안 붙었다 | `aws sts get-caller-identity`. 비면 인스턴스에 IAM 역할 연결 |
| `AccessDenied`인데 자격증명은 있음 | 정책 접두사 밖을 건드렸다 | 2-A 정책은 `videos/` 읽기·`reports/` 쓰기뿐이다. `videos/`에 쓰려 한 것은 아닌지 |
| 서버는 뜨는데 첫 판정이 타임아웃 | 첫 요청에 워밍업이 겹친다 | 5-3의 curl로 미리 한 번 깨워 둔다 |
| 영상은 받았는데 측정에서 멈춤/느림 | RT-DETR·ViTPose를 그때 HF에서 받고 있다 | 5-4를 먼저 돌린다. 이그레스가 막혔으면 그쪽부터 |

로그:
```bash
sudo journalctl -u supersub-vllm -f              # vLLM 실시간
sudo journalctl -u supersub-vllm -n 200 --no-pager
nvidia-smi -l 2                                   # GPU 사용량 추적
```

---

## 9. 아직 안 한 것

이 런북이 **덮지 않는** 것들이다. 지금 필요 없어서 뺐지 실수가 아니다.

- **자동 트리거** — S3 이벤트나 폴링 워커가 없다. 수동 CLI 1건 실행이다.
  중복 처리·재시도·상태 저장이 필요해지면 그때 만든다.
- **`api.py`를 EC2에서 서비스로 띄우기** — 8080 유닛을 만들지 않았다.
  인증·타임아웃·동시성 설계가 먼저다.
- **다중 인스턴스 / 오토스케일링** — 한 대다.
- **모니터링·알림** — CloudWatch 에이전트를 안 붙였다. `journalctl`로 본다.
- **계정 분리** — 팀 계정을 공유한다(위 "격리 수준"). 네트워크는 전용 VPC로
  갈랐지만 결제·할당량·관리자 권한은 공유된다. 상용 단계의 판단거리다.

## 관련

- 미결 1번(EXAONE NC 라이선스), 9번(4K host RAM), 19번(이 배포가 연 것):
  [`jekyll/pages/pending.markdown`](../../jekyll/pages/pending.markdown)
- 파이프라인 구조·스윙 측 지정: [`agent/README.md`](../README.md)
- 판정 백엔드 두 갈래: `src/supersub_agent/judge.py`의 `Judge` docstring
