#!/usr/bin/env bash
# EXAONE 4.0 1.2B 가중치를 S3에서 로컬 EBS로 내려받는다.
#
# **vLLM은 s3:// 경로를 직접 읽지 못한다.** 로컬 디렉터리로 받아 놓고 그 경로로
# 띄운다. 그래서 이 스크립트가 vLLM 유닛의 ExecStartPre로 걸려 있다 — 인스턴스를
# 껐다 켜도(EBS는 남지만 새 인스턴스면 비어 있다) 기동 전에 채워진다.
#
#   SUPERSUB_MODEL_S3=s3://내-버킷/models/exaone-4.0-1.2b ./sync_model.sh
#
# SUPERSUB_MODEL_S3 를 **비워 두면 S3를 건너뛰고** 이미 받아 둔 로컬 가중치로
# 뜬다. IAM 역할을 아직 못 붙인 인스턴스(README-console 2-C)에서 이 스크립트가
# ExecStartPre 로 걸려 있는 채 aws 호출에서 죽으면, 가중치가 디스크에 멀쩡히
# 있는데도 vLLM 이 기동하지 못한다. 건너뛰더라도 아래 구성 확인은 그대로 한다.
set -euo pipefail

MODEL_S3="${SUPERSUB_MODEL_S3:-}"
MODEL_DIR="${SUPERSUB_MODEL_DIR:-/opt/supersub/models/exaone-4.0-1.2b}"

mkdir -p "$MODEL_DIR"

if [[ -z "$MODEL_S3" ]]; then
  echo "[sync] SUPERSUB_MODEL_S3 가 비어 있다 — S3를 건너뛰고 $MODEL_DIR 를 그대로 쓴다"
else
  # --delete를 쓰지 않는다. 로컬에만 있는 파일을 지우는 것보다, 중간에 끊긴
  # 동기화가 남긴 부분 파일을 다음 sync가 크기·수정시각으로 다시 받는 편이 안전하다.
  echo "[sync] $MODEL_S3 → $MODEL_DIR"
  aws s3 sync "$MODEL_S3" "$MODEL_DIR" --only-show-errors
fi

# 최소 구성 확인 — config.json이 없으면 vLLM이 한참 뒤에 알아보기 어려운
# 오류로 죽는다. 여기서 걸리면 원인이 "모델이 안 받아졌다"로 바로 읽힌다.
for f in config.json tokenizer_config.json; do
  [[ -f "$MODEL_DIR/$f" ]] || {
    echo "[sync] 실패: $MODEL_DIR/$f 없음" >&2
    [[ -z "$MODEL_S3" ]] && echo "[sync] S3를 건너뛰었다 — 가중치를 먼저 받을 것 (README 5-1)" >&2
    exit 1
  }
done

echo "[sync] 완료 — $(du -sh "$MODEL_DIR" | cut -f1)"
