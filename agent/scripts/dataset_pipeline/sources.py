"""종목별 데이터 출처 어댑터.

## 🔴 명세와 실제가 어긋나는 곳 — 여기가 그 기록이다

2026-09-04에 세 출처를 **실제로 조회해서** 확인했다. 추측이 아니다.

| 종목 | 명세 | 실제 |
|---|---|---|
| ⚽ | SoccerNet **Clips-720p-10s**, HF 선택 다운로드 | HF `SoccerNet` 조직에 그런 저장소가 **없다.** 720p 원본(`SoccerNet_raw_HQ`)은 `gated=manual` 이고 파일이 안 올라와 있다(NDA 배포). **대안으로 `SushantGautam/SoccerNet-10s-5Class`** 를 쓴다 — 10초 클립 34,050개가 **파일 하나씩** 올라와 있어 선택 다운로드가 된다. 🔴 다만 **224p** 다 |

🔴 **야구·농구 어댑터는 2026-09-11 에 지웠다** (팀 방향이 축구 단일 종목으로
정해졌다). 되살릴 일이 생길 때 같은 조사를 반복하지 않도록 **그때 확인한
것만** 남긴다 — 코드는 git 이력에 있다.

- ⚾ `hbfreed/Picklebot-130K` 는 실재하나 영상이 **단일 `.tar.xz` 28.4GB** 라
  파일 단위 선택 다운로드가 **원리적으로 불가능**하다. CSV(34MB)로 고르고
  아카이브를 한 번 받아 꺼내는 방식이었다. 해상도 224×224 · **15fps**.
- 🏀 PL-NBA 프리트림 클립은 **바이두넷디스크**로만 배포돼 자동 다운로드가
  안 된다(사람이 받아 둔 폴더를 읽는 어댑터였다). **상업적 이용 금지**라
  서비스 경로에는 애초에 못 쓴다(미결 15번과 같은 축).

## 🔴 받기 전에 알아야 할 것 두 가지

**(1) 224p 축구 클립으로 자세를 재는 것은 무리다.** 우리 경로는 RT-DETR +
ViTPose top-down 이고, 방송 화면에서 선수 하나는 그 안에서 아주 작다.
`www/src/lib/personDetector.ts` 가 "화면 전체를 256px 로 줄이면 멀리 있는
선수가 가로 30px 남짓이라 손목·발목을 믿을 수 없다"고 적어 둔 것과 같은 문제이고,
224p 원본은 그보다 나쁘다. **받는 것은 되지만 나온 지표를 믿을 근거가 없다.**

**(2) "이벤트 클립"이지 "동작 클립"이 아니다.** SoccerNet-10s 는
Goal/Foul/Throw-in 같은 방송 이벤트(카메라 전환·리플레이 포함)다. 우리 루브릭은
**(종목, 동작) 단위**로 한 선수의 한 동작을 본다(미결 3번). 이벤트 클립은 그
단위가 아니다.

라이선스: SoccerNet 계열은 NDA 조건이 붙는다 — 미결 15번과 같은 축이다.
"""
from __future__ import annotations

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


class LocalFolder:
    """이미 가진 폴더를 그대로 카탈로그로 쓴다.

    🔴 **먼저 이것부터 보라.** 2026-09-04에 세 공개 데이터셋을 뒤지고 나서
    확인한 것인데, **저장소가 이미 들고 있는 클립이 후보들보다 낫다.**

    | 가진 것 | 해상도 · fps | 후보 |
    |---|---|---|
    | `data/goldenset/soccerkicks_video` 19건 | 522×358 \~ **1280×720**, 24\~30fps | UCF101 축구 320×240 |

    전부 **단독 선수 · 단일 동작**이라 방송 이벤트 클립의 문제(여러 선수 · 컷
    전환)가 없다. 게이트도 대용량 다운로드도 필요 없다.

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
    raise ValueError(
        f"모르는 종목: {sport!r}. 축구 단일 종목이다 (2026.09.11) — "
        "야구(Picklebot-130K)·농구(PL-NBA) 출처는 함께 지웠다."
    )
