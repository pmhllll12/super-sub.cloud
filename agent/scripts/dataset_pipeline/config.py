"""배치 파이프라인 설정 — 저장 위치, 배치 크기, 정리 방식, 진행 커서.

## 🔴 `D:/sports_dataset` 은 이 기계에서 `/mnt/d/sports_dataset` 이다

개발 환경이 WSL2다. 윈도우 경로를 그대로 쓰면 리눅스에서는 `D:` 라는 이름의
**상대 경로 폴더**가 저장소 안에 조용히 만들어진다 — 용량을 D드라이브로
빼려던 목적이 정확히 반대로 뒤집힌다. 그래서 윈도우 표기를 받아 번역한다.

    D:/sports_dataset   →  /mnt/d/sports_dataset   (WSL)
    D:/sports_dataset   →  D:/sports_dataset       (윈도우 파이썬)

`SPORTS_DATASET_ROOT` 환경변수로 덮어쓸 수 있다.
"""
from __future__ import annotations

import json
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path

# 명세가 정한 기본 위치. 윈도우 표기 그대로 두고 아래에서 번역한다.
DEFAULT_ROOT = "D:/sports_dataset"

SPORTS = ("soccer", "baseball", "basketball")

# 한 번에 받아서 처리할 클립 수.
BATCH_SIZE = 100

_DRIVE = re.compile(r"^([A-Za-z]):[/\\](.*)$")


def translate_root(value: str) -> Path:
    """윈도우 드라이브 표기를 지금 OS에서 실제로 쓸 수 있는 경로로."""
    m = _DRIVE.match(value)
    if not m or platform.system() == "Windows":
        return Path(value)
    drive, rest = m.group(1).lower(), m.group(2).replace("\\", "/")
    return Path(f"/mnt/{drive}") / rest


def root() -> Path:
    return translate_root(os.environ.get("SPORTS_DATASET_ROOT", DEFAULT_ROOT))


_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(clip_id: str, suffix: str = ".mp4", keep: int = 60) -> str:
    """디스크에 쓸 파일 이름. **id 자체는 바꾸지 않는다.**

    🔴 여기는 D드라이브 = NTFS 다. SoccerNet 클립 이름은 27,240건 **전부**
    `|` 를 담고 있고 길이가 110자를 넘는다. WSL 의 drvfs 는 그걸 통과시키지만
    같은 폴더를 윈도우에서 열면 이름이 깨져 보이고, 경로가 깊어지면 MAX_PATH
    에도 걸린다.

    그래서 **디스크 이름만** 안전하게 줄이고, 원래 id 는 커서와 결과 JSON 이
    그대로 들고 있는다. 줄이면 충돌할 수 있으므로 원본 id 의 해시를 붙인다 —
    잘린 앞부분이 같아도 파일은 갈린다.
    """
    import hashlib

    stem = _UNSAFE.sub("_", clip_id)[:keep].rstrip(". ")
    tag = hashlib.sha1(clip_id.encode("utf-8")).hexdigest()[:8]
    return f"{stem}_{tag}{suffix}"


def sport_dir(sport: str, *parts: str) -> Path:
    """`<root>/<종목>/...`. 없으면 만든다."""
    if sport not in SPORTS:
        raise ValueError(f"모르는 종목: {sport!r} (가능: {', '.join(SPORTS)})")
    path = root().joinpath(sport, *parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- 정리 방식 --------------------------------------------------------------
#
# 배치 하나를 다 분석한 뒤 원본 클립을 어떻게 할 것인가.
#
#   delete  D드라이브에서 지운다. 가장 싸고 되돌릴 수 없다
#   s3      S3에 올린 **뒤** 지운다. 올리기에 실패하면 지우지 않는다
#   keep    아무것도 안 한다. 처음 돌려 볼 때 쓴다
#
# 🔴 기본값이 `keep` 인 이유: 지우는 것이 기본이면 처음 돌려 보는 사람이
# 원본을 잃는다. 지우는 것은 **명시적으로** 골라야 한다.
STORAGE_MODES = ("keep", "delete", "s3")
DEFAULT_STORAGE_MODE = "keep"


@dataclass(frozen=True)
class Settings:
    sport: str
    batch_size: int = BATCH_SIZE
    storage_mode: str = DEFAULT_STORAGE_MODE
    # s3 모드에서만 쓴다. `s3://버킷/접두사`
    s3_prefix: str | None = None
    s3_region: str | None = None
    # 🔴 루브릭을 기본값에 맡기지 않는다 — 미결 17번 「하지 말 것」.
    # 안 주면 야구 영상이 축구 루브릭으로 채점된다.
    rubric: str = ""
    # pose 만 뽑을지, 판정(LLM)까지 갈지.
    stage: str = "pose"

    def validate(self) -> None:
        if self.storage_mode not in STORAGE_MODES:
            raise ValueError(f"모르는 정리 방식: {self.storage_mode!r}")
        if self.storage_mode == "s3" and not self.s3_prefix:
            raise ValueError("s3 모드에는 --s3-prefix 가 필요하다 (s3://버킷/접두사)")
        if not self.rubric:
            raise ValueError(
                "루브릭을 명시할 것 — 기본값에 기대면 종목이 어긋나도 조용히 채점된다"
            )


# --- 진행 커서 --------------------------------------------------------------
#
# 어디까지 처리했는지. **파일로 남겨야** 중간에 끊겨도 이어서 돈다 —
# 배치를 지우고 나면 "받은 적 있는지"를 디스크로는 알 수 없기 때문이다.


class Cursor:
    """`<root>/<종목>/_state.json`. 처리한 클립 id 와 배치 번호를 들고 있다."""

    def __init__(self, sport: str) -> None:
        self.path = sport_dir(sport) / "_state.json"
        self.done: set[str] = set()
        self.batch_no = 0
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.done = set(data.get("done", []))
            self.batch_no = int(data.get("batch_no", 0))

    def mark(self, clip_ids: list[str]) -> None:
        self.done.update(clip_ids)
        self.batch_no += 1
        self.save()

    def save(self) -> None:
        self.path.write_text(
            json.dumps(
                {"batch_no": self.batch_no, "done": sorted(self.done)},
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
