"""종목별 데이터 출처 어댑터.

## 🔴 명세와 실제가 어긋나는 곳 — 여기가 그 기록이다

2026-09-04에 세 출처를 **실제로 조회해서** 확인했다. 추측이 아니다.

| 종목 | 명세 | 실제 |
|---|---|---|
| ⚽ | SoccerNet **Clips-720p-10s**, HF 선택 다운로드 | HF `SoccerNet` 조직에 그런 저장소가 **없다.** 720p 원본(`SoccerNet_raw_HQ`)은 `gated=manual` 이고 파일이 안 올라와 있다(NDA 배포). **대안으로 `SushantGautam/SoccerNet-10s-5Class`** 를 쓴다 — 10초 클립 34,050개가 **파일 하나씩** 올라와 있어 선택 다운로드가 된다. 🔴 다만 **224p** 다 |
| ⚾ | 메타데이터 필터 후 **선택 다운로드** | `hbfreed/Picklebot-130K` 는 있다. 그런데 영상이 **단일 `picklebot_130k.tar.xz` 28.4GB** 다 — 파일 단위 선택 다운로드가 **원리적으로 불가능**하다. CSV(34MB)만 먼저 받아 고르고, 아카이브는 한 번 받아 **고른 것만 꺼낸다** |
| 🏀 | PL-NBA pre-trimmed 100개 | HF에 없다. 논문(arXiv 2608.19646)과 GitHub(`holhouse/PL-NBA-Dataset`)는 실재하나 **프리트림 클립이 바이두넷디스크**로만 배포된다 — 스크립트로 자동으로 받을 수 없다. **사람이 받아 둔 폴더를 읽는** 어댑터로 만든다 |

## 🔴 받기 전에 알아야 할 것 두 가지

**(1) 224p 축구 클립으로 자세를 재는 것은 무리다.** 우리 경로는 RT-DETR +
ViTPose top-down 이고, 방송 화면에서 선수 하나는 그 안에서 아주 작다.
`www/src/lib/personDetector.ts` 가 "화면 전체를 256px 로 줄이면 멀리 있는
선수가 가로 30px 남짓이라 손목·발목을 믿을 수 없다"고 적어 둔 것과 같은 문제이고,
224p 원본은 그보다 나쁘다. **받는 것은 되지만 나온 지표를 믿을 근거가 없다.**

**(2) 셋 다 "이벤트 클립"이지 "동작 클립"이 아니다.** SoccerNet-10s 는
Goal/Foul/Throw-in 같은 방송 이벤트(카메라 전환·리플레이 포함), PL-NBA 는
공격 하나(평균 12.11초, 여러 선수·여러 이벤트)다. 우리 루브릭은 **(종목, 동작)
단위**로 한 선수의 한 동작을 본다(미결 3번). 이벤트 클립은 그 단위가 아니다.

라이선스: PL-NBA 는 **상업적 이용 금지**(연구용 한정), SoccerNet 계열은 NDA
조건이 붙는다 — 미결 15번과 같은 축이다.
"""
from __future__ import annotations

import csv
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from . import config


@dataclass(frozen=True)
class ClipRef:
    """카탈로그의 한 줄. **아직 내려받지 않은 상태**의 참조다."""

    clip_id: str          # 커서가 쓰는 고유 id
    remote: str           # 출처 안에서의 위치 (repo 내 경로 · 아카이브 멤버 이름 …)
    label: str = ""       # 이벤트 종류 등, 있으면 기록만 한다
    note: str = ""


class Source(Protocol):
    key: str

    def catalog(self) -> list[ClipRef]: ...

    def fetch(self, clip: ClipRef, dest_dir: Path) -> Path: ...


# --- ⚽ 축구 ---------------------------------------------------------------


class SoccerNet10s:
    """`SushantGautam/SoccerNet-10s-5Class` — 클립 하나가 파일 하나다.

    **명세가 요구한 "필요한 파일만 콕 집어서" 가 이 출처에서만 그대로 된다.**
    `list_repo_files` 로 목록만 받고(수 MB), 고른 것만 `hf_hub_download` 한다.

    ⚠️ `gated=auto` 다 — 저장소 페이지에서 약관에 동의하고
    `huggingface-cli login` 을 해 두어야 한다. 안 하면 401 이 난다.
    """

    key = "soccer"
    repo_id = "SushantGautam/SoccerNet-10s-5Class"
    # 224p 라는 사실을 파일 이름이 들고 있다. 나중에 헷갈리지 않게 남긴다.
    resolution_note = "224p (720p 아님 — 모듈 첫머리 경고 참고)"

    def __init__(self, split: str = "train", event: str | None = None) -> None:
        self.split, self.event = split, event

    def catalog(self) -> list[ClipRef]:
        from huggingface_hub import list_repo_files

        files = list_repo_files(self.repo_id, repo_type="dataset")
        out: list[ClipRef] = []
        for f in files:
            if not f.endswith(".mp4"):
                continue
            parts = f.split("/")
            if len(parts) < 4 or parts[1] != self.split:
                continue
            label = parts[2]
            if self.event and label != self.event:
                continue
            # 파일명이 곧 고유 id 다. 경로째 쓰면 커서 파일이 쓸데없이 길어진다.
            out.append(ClipRef(clip_id=parts[-1][:-4], remote=f, label=label))
        # 정렬해 둔다 — 배치 경계가 실행마다 달라지면 "다음 100개"가 뜻을 잃는다.
        return sorted(out, key=lambda c: c.clip_id)

    def fetch(self, clip: ClipRef, dest_dir: Path) -> Path:
        from huggingface_hub import hf_hub_download

        got = hf_hub_download(
            self.repo_id, clip.remote, repo_type="dataset",
            # 🔴 캐시를 D드라이브 안에 둔다. 기본값은 ~/.cache (C드라이브)라
            # 용량을 D로 빼려던 목적이 무너진다.
            cache_dir=str(config.sport_dir(self.key, "_hf_cache")),
        )
        # 🔴 원래 id 가 아니라 **안전한 이름**으로 쓴다 (NTFS · MAX_PATH).
        dest = dest_dir / config.safe_name(clip.clip_id, ".mp4")
        # 캐시본은 symlink 일 수 있다. 배치를 지울 때 캐시까지 지우지 않도록 복사한다.
        dest.write_bytes(Path(got).read_bytes())
        return dest


# --- ⚾ 야구 ---------------------------------------------------------------


class Picklebot130K:
    """`hbfreed/Picklebot-130K` — CSV로 고르고, 아카이브에서 꺼낸다.

    🔴 **선택 다운로드가 안 되는 출처다.** 영상이 `picklebot_130k.tar.xz`
    **하나(28.4GB)** 뿐이라 파일 단위로 집어올 수가 없다. 그래서 이렇게 한다.

        1. CSV 세 개(합 34MB)만 먼저 받아 **메타데이터로 고른다** — 여기까지는
           명세대로다
        2. 아카이브는 **한 번만** 받는다(28.4GB, D드라이브)
        3. 배치마다 고른 멤버만 **꺼낸다**. 배치 정리는 꺼낸 것만 지운다

    28.4GB 를 받기 싫으면 이 출처는 쓸 수 없다. 그것이 이 데이터셋의 성질이지
    파이프라인의 한계가 아니다.

    투구 클립이라 `baseball_pitching` 루브릭과 맞는다 — 야구 **타격** 루브릭이
    없는 문제(미결 3번)를 비껴간다.
    """

    key = "baseball"
    repo_id = "hbfreed/Picklebot-130K"
    archive = "picklebot_130k.tar.xz"

    def __init__(self, split: str = "val", label: str | None = None) -> None:
        # 기본을 val 로 둔 이유: train CSV 가 21MB 로 가장 크고, 처음 돌려 볼 때
        # 필요한 것은 전수가 아니다.
        self.split, self.label = split, label
        self._tar: tarfile.TarFile | None = None

    def _csv(self) -> Path:
        from huggingface_hub import hf_hub_download

        return Path(hf_hub_download(
            self.repo_id, f"picklebot_130k_{self.split}.csv", repo_type="dataset",
            cache_dir=str(config.sport_dir(self.key, "_hf_cache")),
        ))

    # 🔴 컬럼을 **명시한다.** 휴리스틱으로 고르게 두었다가 `video_link`
    # (baseballsavant URL)를 파일 이름으로 집었다 — "video"가 "file"보다 먼저
    # 걸렸기 때문이다. 스키마가 바뀌면 조용히 틀리는 것보다 멈추는 편이 낫다.
    FILE_COL = "filename"        # 예: clip_46567.mp4 — 아카이브 안의 이름
    LABEL_COL = "pitch_result"   # "Ball" 또는 "Called Strike"

    def catalog(self) -> list[ClipRef]:
        rows = list(csv.DictReader(open(self._csv(), encoding="utf-8")))
        if not rows:
            return []
        cols = set(rows[0].keys())
        missing = {self.FILE_COL, self.LABEL_COL} - cols
        if missing:
            raise RuntimeError(
                f"CSV 스키마가 바뀌었다. 없는 컬럼: {sorted(missing)} · "
                f"있는 컬럼: {sorted(cols)}"
            )
        out: list[ClipRef] = []
        for r in rows:
            name = (r[self.FILE_COL] or "").strip()
            if not name:
                continue
            lab = (r[self.LABEL_COL] or "").strip()
            if self.label and lab != self.label:
                continue
            out.append(ClipRef(clip_id=Path(name).stem, remote=name, label=lab,
                               note=f"{r.get('pitch','')} {r.get('mph','')}mph"))
        return sorted(out, key=lambda c: c.clip_id)

    def _archive_path(self) -> Path:
        from huggingface_hub import hf_hub_download

        print(f"  [야구] 아카이브를 받는다 (28.4GB, 한 번만) — {self.archive}")
        return Path(hf_hub_download(
            self.repo_id, self.archive, repo_type="dataset",
            cache_dir=str(config.sport_dir(self.key, "_hf_cache")),
        ))

    def prefetch(self, clips: list[ClipRef], dest_dir: Path) -> dict[str, Path]:
        """🔴 **배치를 한 번의 순차 통과로 꺼낸다.**

        `.tar.xz` 는 스트림 전체가 한 덩어리로 압축돼 있어 **랜덤 접근이 없다** —
        멤버 하나를 꺼낼 때마다 앞에서부터 다시 푼다. 100건을 하나씩 꺼내면
        28GB 를 100번 훑는 셈이다. 그래서 원하는 이름을 집합으로 들고 **처음부터
        끝까지 한 번만** 지나가며 걸리는 대로 쓴다.

        아카이브 안 경로에 상위 폴더가 있을 수 있어 **basename 으로 맞춘다.**
        """
        want = {c.remote: c for c in clips}
        found: dict[str, Path] = {}
        with tarfile.open(self._archive_path(), "r:xz") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                base = Path(member.name).name
                clip = want.get(base)
                if clip is None:
                    continue
                src = tar.extractfile(member)
                if src is None:
                    continue
                dest = dest_dir / config.safe_name(
                    clip.clip_id, Path(base).suffix or ".mp4")
                dest.write_bytes(src.read())
                found[clip.clip_id] = dest
                if len(found) == len(want):
                    break   # 다 찾았으면 남은 28GB를 더 풀 이유가 없다
        return found

    def fetch(self, clip: ClipRef, dest_dir: Path) -> Path:
        # 단건 호출은 아카이브 전체를 다시 푸는 일이라 **쓰지 않는다.**
        # run.py 가 prefetch 를 먼저 찾는다.
        raise RuntimeError(
            "Picklebot 은 단건 fetch 를 쓰지 않는다 — prefetch 로 배치를 한 번에 꺼낸다"
        )


# --- 🏀 농구 ---------------------------------------------------------------


class PLNBALocal:
    """PL-NBA — **사람이 받아 둔 폴더를 읽는다.**

    🔴 자동으로 받을 수 없다. 프리트림 클립이 **바이두넷디스크**로만 배포되고
    (`holhouse/PL-NBA-Dataset` README), 그건 중국 계정과 전용 클라이언트가
    필요해 스크립트로 집어올 수 없다. 없는 자동화를 흉내 내는 대신 **어디에
    두면 되는지 말하고 멈춘다.**

        <root>/basketball/_incoming/*.mp4

    라이선스: **연구용 한정, 상업적 이용 금지.** 서비스 경로에 넣지 말 것
    (미결 15번과 같은 축이다).
    """

    key = "basketball"
    drop = "_incoming"

    def catalog(self) -> list[ClipRef]:
        folder = config.sport_dir(self.key, self.drop)
        files = sorted(p for p in folder.iterdir()
                       if p.suffix.lower() in (".mp4", ".mkv", ".mov"))
        if not files:
            raise SystemExit(
                "🔴 PL-NBA 클립이 없다. 자동 다운로드가 불가능한 출처다.\n"
                f"   프리트림 클립을 내려받아 여기에 두고 다시 돌릴 것:\n"
                f"     {folder}\n"
                "   배포처: https://github.com/holhouse/PL-NBA-Dataset\n"
                "     → README 의 바이두넷디스크 링크 (pwd=pnba)\n"
                "   ⚠️ 연구용 한정 · 상업적 이용 금지"
            )
        return [ClipRef(clip_id=p.stem, remote=str(p)) for p in files]

    def fetch(self, clip: ClipRef, dest_dir: Path) -> Path:
        dest = dest_dir / config.safe_name(
            clip.clip_id, Path(clip.remote).suffix or ".mp4")
        # 원본을 옮기지 않고 복사한다 — 배치 정리가 원본을 지우면 안 된다.
        dest.write_bytes(Path(clip.remote).read_bytes())
        return dest


class LocalFolder:
    """이미 가진 폴더를 그대로 카탈로그로 쓴다.

    🔴 **먼저 이것부터 보라.** 2026-09-04에 세 공개 데이터셋을 뒤지고 나서
    확인한 것인데, **저장소가 이미 들고 있는 클립이 후보들보다 낫다.**

    | 가진 것 | 해상도 · fps | 후보 |
    |---|---|---|
    | `data/goldenset/soccerkicks_video` 19건 | 522×358 \~ **1280×720**, 24\~30fps | UCF101 축구 320×240 |
    | `data/bball_shot.mp4` · `bball_layup_trim.mp4` | **1920×1080**, 24fps | SpaceJam **171×128 · 16프레임** |
    | `data/baseball_pitch_trim.mp4` | **2160×3840**, 25fps | Roboflow 포즈 = **정지 이미지** |

    전부 **단독 선수 · 단일 동작**이라 방송 이벤트 클립의 문제(여러 선수 · 컷
    전환)가 없다. 게이트도 28GB 다운로드도 바이두넷디스크도 필요 없다.

    ⚠️ 그래도 **자세 정답은 없다.** 축구 킥의 `contact_frame` 은 공-발목
    최근접에서 자동 도출한 참조이고 ±2프레임 불확실성을 갖는다(미결 5번 정정).
    """

    key = "local"
    SUFFIXES = (".mp4", ".avi", ".mkv", ".mov", ".webm")

    def __init__(self, path: str | Path, sport: str = "soccer") -> None:
        self.folder = Path(path)
        self.key = sport

    def catalog(self) -> list[ClipRef]:
        if not self.folder.exists():
            raise SystemExit(f"폴더가 없다: {self.folder}")
        files = sorted(p for p in self.folder.rglob("*")
                       if p.suffix.lower() in self.SUFFIXES)
        if not files:
            raise SystemExit(f"영상이 없다: {self.folder}")
        return [ClipRef(clip_id=p.stem, remote=str(p), label=p.parent.name)
                for p in files]

    def fetch(self, clip: ClipRef, dest_dir: Path) -> Path:
        # 🔴 원본을 옮기지 않고 복사한다 — 배치 정리(delete/s3)가 원본을
        # 지우면 저장소의 자산이 사라진다.
        dest = dest_dir / config.safe_name(
            clip.clip_id, Path(clip.remote).suffix or ".mp4")
        dest.write_bytes(Path(clip.remote).read_bytes())
        return dest


def get_source(sport: str, local_dir: str | None = None, **kw) -> Source:
    # 로컬 폴더가 주어지면 그것이 이긴다 — 종목과 무관하게 쓴다.
    if local_dir:
        return LocalFolder(local_dir, sport=sport)
    if sport == "soccer":
        return SoccerNet10s(**kw)
    if sport == "baseball":
        return Picklebot130K(**kw)
    if sport == "basketball":
        return PLNBALocal()
    raise ValueError(f"모르는 종목: {sport!r}")
