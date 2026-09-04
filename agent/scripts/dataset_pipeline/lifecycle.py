"""배치를 다 쓴 뒤 원본 클립을 어떻게 할 것인가.

## 🔴 올리기에 실패하면 지우지 않는다

`s3` 모드의 순서는 **올린다 → 확인한다 → 지운다** 이고, 어느 단계든 실패하면
**그 파일은 남긴다.** 반대로 하면 네트워크가 한 번 끊길 때 원본이 사라진다.
지우는 것은 되돌릴 수 없으므로 실패 쪽으로 기운다.

S3 코드는 새로 쓰지 않는다 — `supersub_agent.storage` 가 이미 boto3 를 선택
의존성으로 감싸고 있고(`uv sync --extra aws`), 없으면 알아볼 수 있는 오류를
낸다. 두 벌이 되면 자격증명 해석이 갈린다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from supersub_agent import storage


@dataclass
class Outcome:
    uploaded: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    def summary(self) -> str:
        line = (f"올림 {len(self.uploaded)} · 지움 {len(self.deleted)} · "
                f"남김 {len(self.kept)} · 실패 {len(self.failed)}")
        for name, why in self.failed[:5]:
            line += f"\n    ✗ {name}: {why}"
        if len(self.failed) > 5:
            line += f"\n    … 외 {len(self.failed) - 5}건"
        return line


def _remove(path: Path, out: Outcome) -> None:
    try:
        path.unlink()
        out.deleted.append(path.name)
    except OSError as exc:
        # 지우기 실패는 다음 배치의 용량 문제로 이어지지만 분석을 되돌리지는
        # 않는다. 기록하고 넘어간다.
        out.failed.append((path.name, f"삭제 실패: {exc}"))


def purge(
    files: list[Path],
    mode: str,
    *,
    s3_prefix: str | None = None,
    s3_region: str | None = None,
    batch_no: int = 0,
) -> Outcome:
    """배치 파일들을 정리한다. **한 파일의 실패가 나머지를 막지 않는다.**"""
    out = Outcome()

    if mode == "keep":
        out.kept = [f.name for f in files]
        return out

    if mode == "delete":
        for f in files:
            _remove(f, out)
        return out

    if mode != "s3":
        raise ValueError(f"모르는 정리 방식: {mode!r}")

    if not s3_prefix:
        raise ValueError("s3 모드에는 s3_prefix 가 필요하다")

    for f in files:
        if not f.exists():
            out.failed.append((f.name, "파일이 없다"))
            continue
        try:
            uri = storage.join_uri(s3_prefix, f"batch_{batch_no:04d}", f.name)
            storage.upload_file(f, uri, region=s3_region)
        except Exception as exc:  # noqa: BLE001 — 어떤 실패든 원본은 지키고 넘어간다
            out.failed.append((f.name, f"업로드 실패({type(exc).__name__}): {exc}"))
            out.kept.append(f.name)
            continue
        out.uploaded.append(f.name)
        # 🔴 올린 **뒤에만** 지운다.
        _remove(f, out)

    return out
