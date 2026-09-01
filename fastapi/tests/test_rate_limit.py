"""인증 엔드포인트 요청 제한. 5장 SEC-009.

한도 자체(창·경계·키 분리)는 `SlidingWindowLimiter` 를 직접 불러 본다 — HTTP 로
확인하려면 시간을 실제로 기다려야 한다.
"""

import pytest

from app.core.errors import ApiError
from app.core.rate_limit import AUTH_LIMIT, SlidingWindowLimiter
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)
from tests.conftest import V1, error_code


class TestLimiter:
    def test_한도까지는_통과하고_넘으면_막는다(self):
        limiter = SlidingWindowLimiter(limit=3, window_seconds=60)

        for _ in range(3):
            limiter.check("같은-출처")

        with pytest.raises(ApiError) as caught:
            limiter.check("같은-출처")
        assert caught.value.status_code == 429
        assert caught.value.code == "TOO_MANY_REQUESTS"

    def test_출처가_다르면_따로_센다(self):
        """한 사람이 몰아친다고 다른 사람까지 막히면 그게 서비스 거부다."""
        limiter = SlidingWindowLimiter(limit=1, window_seconds=60)

        limiter.check("출처-A")
        limiter.check("출처-B")  # A 가 다 썼어도 B 는 통과한다

        with pytest.raises(ApiError):
            limiter.check("출처-A")

    def test_창이_지나면_다시_통과한다(self):
        """창을 0.05초로 줄여 실제로 시간이 지나가게 한다."""
        import time

        limiter = SlidingWindowLimiter(limit=1, window_seconds=0.05)
        limiter.check("출처")
        with pytest.raises(ApiError):
            limiter.check("출처")

        time.sleep(0.06)
        limiter.check("출처")  # 지나간 기록은 버려진다

    def test_오래된_출처는_쓸려_나간다(self):
        """안 쓸면 주소를 바꿔 가며 보내는 쪽이 메모리를 늘릴 수 있다."""
        import time

        from app.core import rate_limit

        limiter = SlidingWindowLimiter(limit=5, window_seconds=0.05)
        for i in range(rate_limit._SWEEP_AT + 2):
            limiter.check(f"출처-{i}")
        assert len(limiter._hits) > rate_limit._SWEEP_AT

        # 창이 지난 뒤 다음 요청이 들어오는 순간 쓸어낸다.
        time.sleep(0.06)
        limiter.check("새-출처")

        assert len(limiter._hits) == 1


class TestAuthEndpoints:
    def test_로그인을_한도_넘게_시도하면_429(self, client):
        for _ in range(AUTH_LIMIT):
            client.post(
                f"{V1}/auth/login",
                json={"email": DEMO_EMAIL, "password": "wrong-password"},
            )

        res = client.post(
            f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert res.status_code == 429
        # 계약의 에러 봉투를 그대로 쓴다 — 클라이언트가 code 로 분기할 수 있어야 한다.
        assert error_code(res) == "TOO_MANY_REQUESTS"

    def test_경로가_다르면_따로_센다(self, client):
        for _ in range(AUTH_LIMIT + 1):
            client.post(
                f"{V1}/auth/login",
                json={"email": DEMO_EMAIL, "password": "wrong-password"},
            )

        # 로그인이 막혀도 가입은 살아 있다.
        res = client.post(
            f"{V1}/auth/signup",
            json={
                "email": "still-open@example.com",
                "password": "password12",
                "nickname": "통과",
            },
        )
        assert res.status_code == 201

    def test_제한은_인증_엔드포인트에만_붙는다(self, client):
        """`/me` 는 이미 토큰을 요구한다. 조회까지 묶으면 정상 사용자가 막힌다."""
        for _ in range(AUTH_LIMIT + 1):
            res = client.get(f"{V1}/me", headers={"Authorization": "Bearer nope"})

        assert res.status_code == 401
        assert error_code(res) == "INVALID_TOKEN"

    def test_형식이_틀린_요청도_센다(self, client):
        """본문이 깨진 요청이 무제한이면 제한을 우회하는 길이 된다."""
        for _ in range(AUTH_LIMIT):
            client.post(f"{V1}/auth/login", json={"email": "no-password@example.com"})

        res = client.post(f"{V1}/auth/login", json={"email": "x@example.com"})
        assert res.status_code == 429


class TestRetryAfter:
    """429 에 `Retry-After` 를 싣는다.

    없으면 클라이언트가 **언제 풀리는지 알 수 없어** 스스로 타이머를 만들어야 하고,
    그 값이 서버 창과 어긋나면 너무 일찍 두드리거나 필요 이상으로 기다린다.
    """

    def test_거부된_요청은_창을_밀지_않는다(self):
        """🔴 이것이 `Retry-After` 를 신뢰할 수 있게 하는 전제다.

        거부를 카운트에 넣으면 재시도할 때마다 만료 시각이 뒤로 밀려 **알려 준
        시간이 지나도 안 풀린다.** `check` 가 거부 경로에서 `append` 하지 않는
        것을 여기서 지킨다.
        """
        import time

        limiter = SlidingWindowLimiter(limit=1, window_seconds=0.3)
        limiter.check("출처")

        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:  # 거부되는 동안 계속 두드린다
            with pytest.raises(ApiError):
                limiter.check("출처")

        time.sleep(0.15)  # 최초 요청으로부터 창이 지났다
        limiter.check("출처")  # 두드린 것과 무관하게 풀려야 한다

    def test_남은_시간을_초로_알려준다(self):
        limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
        limiter.check("출처")

        with pytest.raises(ApiError) as caught:
            limiter.check("출처")

        retry_after = caught.value.headers["Retry-After"]
        assert retry_after.isdigit(), "정수 초여야 한다 (HTTP-date 를 쓰지 않는다)"
        assert 1 <= int(retry_after) <= 60

    def test_기다릴수록_값이_줄어든다(self):
        """고정값이 아니라 **남은 시간**임을 확인한다."""
        import time

        limiter = SlidingWindowLimiter(limit=1, window_seconds=10)
        limiter.check("출처")

        with pytest.raises(ApiError) as first:
            limiter.check("출처")
        time.sleep(1.1)
        with pytest.raises(ApiError) as later:
            limiter.check("출처")

        assert int(later.value.headers["Retry-After"]) < int(
            first.value.headers["Retry-After"]
        )

    def test_올림한다(self):
        """내림하면 알려 준 그 시각에 다시 429 를 맞는다."""
        limiter = SlidingWindowLimiter(limit=1, window_seconds=0.4)
        limiter.check("출처")

        with pytest.raises(ApiError) as caught:
            limiter.check("출처")
        assert caught.value.headers["Retry-After"] == "1"  # 0.4 초 → 0 이 아니라 1

    def test_HTTP_응답에도_실린다(self, client):
        for _ in range(AUTH_LIMIT):
            client.post(
                f"{V1}/auth/login",
                json={"email": DEMO_EMAIL, "password": "wrong-password"},
            )

        res = client.post(
            f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert res.status_code == 429
        assert res.headers["Retry-After"].isdigit()

    def test_다른_에러에는_붙지_않는다(self, client):
        """`Retry-After` 는 429 의 계약이다. 401 에 붙으면 뜻이 달라진다."""
        res = client.post(
            f"{V1}/auth/login", json={"email": DEMO_EMAIL, "password": "wrong-password"}
        )
        assert res.status_code == 401
        assert "Retry-After" not in res.headers
