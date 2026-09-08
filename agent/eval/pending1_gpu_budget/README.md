# GPU 예산 실측 (2026-09-08) — 미결 1번

**무엇을 재려고 했나.** `deploy/serve_vllm.sh`의 `--gpu-memory-utilization 0.35`는
계산이 아니라 "1.2B가 들어가고 포즈가 안 죽더라"에서 나온 값이다. EXAONE을
Apache/MIT 모델로 바꾸려는데 후보들이 더 커서, **포즈가 실제로 얼마를 쓰는지**를
알아야 vLLM 몫을 얼마까지 올려도 되는지 정해진다.

조사 회차라 `src/`를 고치지 않았다. `scripts/measure.py`(판정 모델을 안 올리는
포즈 전용 경로)를 그대로 돌리고 `nvidia-smi`로 200ms마다 샘플링했다.

측정 장비: g4dn.xlarge · Tesla T4 **15360 MiB** · 저장소 HEAD `4a951eb`.

## 결과

| 조건 | 파일 | 표본 | 피크 (MiB) |
|---|---|---|---|
| vLLM 정상 상태 (EXAONE 4.0 1.2B, fraction 0.35) | — | — | **5441** |
| 포즈 단독 · 1920×1080 (업로드 상한) | `gpu_1080_clean.csv` | 111 | **903** |
| 포즈 단독 · 2160×3840 (세로 4K) | `gpu_4k_세로.csv` | 165 | **905** |
| 포즈 단독 · 3840×2160 (가로 4K) | `gpu_4k_가로.csv` | 285 | **905** |
| 동시 실행 (vLLM + 포즈) | `gpu_동시.csv` | 113 | **6341** |

`5441 + 900 = 6341`로 정확히 더해진다. **놀고 있는 용량이 9019 MiB다.**

## 🔴 해상도는 VRAM을 올리지 않는다

4K 두 편이 1080p와 같은 905 MiB다. 프로세서가 추론 전에 고정 크기로 줄이기
때문이다 — RT-DETR은 자체 리사이즈, ViTPose는 사람 박스를 잘라 쓴다. 원본
해상도는 GPU에 도달하지 않는다.

**미결 9번(4K에서 host RAM이 먼저 터진다)이 왜 host RAM 문제인지가 이걸로
설명된다.** 4K가 비싼 것은 디코딩된 프레임을 CPU 메모리에 쌓는 쪽이지 GPU가
아니다. 두 항목은 같은 자원을 다투지 않는다.

## 뜻하는 것

포즈에 배정한 약 10GB 중 실제로 쓰는 것은 **0.9GB**다. 넉넉히 4배(3.6GB)를 남겨도
vLLM에 11GB 이상 줄 수 있다. **`GPU_FRACTION`을 올리는 것만으로 후보가 늘어나고,
포즈 코드는 건드릴 이유가 없다** — 건드리면 `features`가 바뀌어 B-6 재실행을
부른다(`agent/CLAUDE.md` 「값비싼 실수 (1)」).

## 이 숫자를 쓸 때 주의할 것

- **`--enforce-eager`가 켜져 있어 1~3GB를 아끼는 중이다.** 속도 때문에 끄면 vLLM이
  그만큼 더 쓴다. 예산을 다시 짤 때 함께 본다
- **200ms 샘플링이라 그보다 짧은 스파이크는 못 잡는다.** 세 조건이 903~905로 거의
  일정해 숨은 봉우리 가능성은 낮아 보이지만, 확정은 아니다
- 4K 두 편은 품질 게이트에서 종료 코드 2로 끝났다(키포인트 유효 프레임 51%·18%,
  기준 70% 미달). 게이트는 **포즈 추출이 끝난 뒤** 걸리므로 피크 측정에는 지장이
  없다 — `m_4k_*.log`에 그 줄이 남아 있다
- **`GPU_FRACTION`은 아직 올리지 않았다.** EXAONE 1.2B는 더 줄 이유가 없고, 쓸
  모델이 정해질 때 함께 바꾸는 것이 맞다

## 재현

```bash
# 인스턴스에서, vLLM을 내리고 포즈만 재는 경우
sudo systemctl stop supersub-vllm && sleep 5
cd ~/super-sub.cloud/agent
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -lms 200 > /tmp/gpu.csv &
SMI=$!
.venv/bin/python scripts/measure.py data/bball_layup_trim.mp4 --limb arm
sleep 1; kill $SMI
sort -n /tmp/gpu.csv | tail -1
sudo systemctl start supersub-vllm
```

🔴 **`pkill -f "nvidia-smi --query-gpu"`를 쓰지 말 것.** 그 패턴이 자기 명령줄과
일치해 셸을 죽인다(2026-09-08에 실제로 그랬다). 배경 프로세스는 PID로 끊는다.
첫 회차에 그 루프가 살아남아 `gpu_1080.csv`를 이후 측정과 겹쳐 써서 오염됐고,
그래서 1080p는 다시 쟀다 — 지금 파일은 `gpu_1080_clean.csv`다.
