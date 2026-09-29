"""`ffmpeg` 로 영상에서 한 장면을 뜬다."""

from __future__ import annotations

import logging
import subprocess

from app.analysis.application.ports.output.poster_port import PosterPort

logger = logging.getLogger(__name__)

#: 어느 지점을 뜨는가. 🔴 **0 이 아니다** — 시작 몇 프레임은 검거나 페이드인인
#: 영상이 많아서 그대로 뜨면 **까만 카드**가 된다(앱도 같은 까닭으로 0.1초를
#: 건너뛰고 있었다).
SEEK_SECONDS = 1.0

#: 뜬 그림의 가로 폭. 카드가 작아서 크게 뜰 까닭이 없고, 작을수록 빨리 간다.
WIDTH = 640

#: 🔴 **반드시 시간 제한을 건다.** 사전 서명 주소가 만료됐거나 저장소가 느리면
#: `ffmpeg` 이 **영영 안 끝난다** — 그러면 요청을 처리하던 일꾼이 묶인다.
TIMEOUT_SECONDS = 20


class FfmpegPoster(PosterPort):
    """🔴 **주소를 그대로 `ffmpeg` 에 물린다 — 내려받지 않는다.**

    서버가 원본을 디스크로 받아 두면 (1) 용량이 크고 (2) 지우는 일이 생기고
    (3) PER-002(업로드·재생이 앱 서버를 지나지 않는다)의 취지에서도 멀어진다.
    `ffmpeg` 은 HTTPS 를 직접 읽고, **필요한 앞부분만** 범위 요청으로 가져온다.

    🔴 **새 S3 권한이 필요 없다** — 넘기는 주소가 재생 주소를 만들던 그 권한으로
    서명된 것이라, `thumbs/` 같은 새 접두사를 쓸 때 걸리는 IAM 문제가 없다.
    """

    def capture(self, media_url: str) -> bytes | None:
        # 🔴 `-ss` 를 `-i` **앞**에 둔다 — 뒤에 두면 처음부터 다 디코딩하며
        #    그 지점까지 간다(느리다). 앞에 두면 그 근처로 바로 건너뛴다.
        argv = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-ss",
            str(SEEK_SECONDS),
            "-i",
            media_url,
            "-frames:v",
            "1",
            "-vf",
            f"scale={WIDTH}:-2",
            "-f",
            "image2",
            "-vcodec",
            "mjpeg",
            "-q:v",
            "4",
            "pipe:1",
        ]
        try:
            done = subprocess.run(  # noqa: S603 - argv 고정, 셸을 안 쓴다
                argv,
                capture_output=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError:
            # 🔴 이미지에 ffmpeg 이 없다 — `fastapi/Dockerfile` 을 보라.
            logger.warning("event=poster_no_ffmpeg")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("event=poster_timeout")
            return None

        if done.returncode != 0 or not done.stdout:
            # 🔴 **실패를 예외로 올리지 않는다.** 형식을 못 읽거나 `SEEK_SECONDS`
            #    보다 짧은 영상이 있고, 그건 "이 영상은 포스터가 없다"이지
            #    서버 오류가 아니다.
            logger.info("event=poster_failed rc=%s", done.returncode)
            return None
        return done.stdout
