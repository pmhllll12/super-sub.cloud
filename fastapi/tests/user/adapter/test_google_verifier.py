"""구글 ID 토큰 검증기. 네트워크를 타지 않는다.

**검증 항목을 하나씩 깨뜨려 전부 401 이 나오는지 본다.** 통과만 보면 "실은 아무것도
검사하지 않는" 상태를 놓친다.
"""

from __future__ import annotations

import pytest

from app.core.errors import ApiError
from app.user.adapter.outbound.google.google_identity_verifier import (
    GoogleIdentityVerifier,
)
from tests.user.google_fake import (
    CLIENT_ID,
    FakeJwkClient,
    make_id_token,
    make_token_signed_by_other_key,
)


def _verifier(audiences=None) -> GoogleIdentityVerifier:
    return GoogleIdentityVerifier(
        audiences=[CLIENT_ID] if audiences is None else audiences,
        jwk_client=FakeJwkClient(),
    )


class TestSuccess:
    def test_유효한_토큰이면_신원을_돌려준다(self):
        identity = _verifier().verify(make_id_token())
        assert identity.provider == "google"
        assert identity.subject == "1234567890"
        assert identity.email == "google-user@super-sub.example"
        assert identity.email_verified is True
        assert identity.display_name == "구글사용자"

    def test_email_verified_가_없으면_확인되지_않은_것으로_본다(self):
        """기본값을 True 로 두면 이메일만 아는 사람이 남의 계정에 연결된다."""
        import jwt as _jwt

        from tests.user import google_fake

        token = _jwt.encode(
            {
                "iss": google_fake.ISSUER,
                "aud": CLIENT_ID,
                "sub": "no-flag",
                "email": "x@y.z",
                "exp": 9999999999,
            },
            google_fake._PRIVATE_PEM,
            algorithm="RS256",
        )
        assert _verifier().verify(token).email_verified is False


class TestRejects:
    def test_다른_앱의_클라이언트_ID_면_거부한다(self):
        """🔴 이걸 안 보면 **아무 구글 앱의 토큰이나 통과한다.**"""
        token = make_id_token(audience="someone-else.apps.googleusercontent.com")
        with pytest.raises(ApiError) as exc:
            _verifier().verify(token)
        assert exc.value.status_code == 401
        assert exc.value.code == "INVALID_GOOGLE_TOKEN"

    def test_발급자가_구글이_아니면_거부한다(self):
        token = make_id_token(issuer="https://evil.example")
        with pytest.raises(ApiError) as exc:
            _verifier().verify(token)
        assert exc.value.code == "INVALID_GOOGLE_TOKEN"

    def test_만료된_토큰을_거부한다(self):
        token = make_id_token(expires_in=-10)
        with pytest.raises(ApiError) as exc:
            _verifier().verify(token)
        assert exc.value.code == "INVALID_GOOGLE_TOKEN"

    def test_다른_키로_서명한_토큰을_거부한다(self):
        """클레임은 전부 정상이고 **서명만 다르다.**

        같은 RS256 으로 다른 키를 쓴다 — HS256 으로 만들면 알고리즘 불일치에서
        걸려서 정작 서명 검증이 도는지는 확인되지 않는다.
        """
        with pytest.raises(ApiError) as exc:
            _verifier().verify(make_token_signed_by_other_key())
        assert exc.value.status_code == 401
        assert exc.value.code == "INVALID_GOOGLE_TOKEN"

    def test_구글_계정이_안_붙어_있으면_503(self):
        """설정이 없으면 조용히 통과시키지 않는다."""
        with pytest.raises(ApiError) as exc:
            _verifier(audiences=[]).verify(make_id_token())
        assert exc.value.status_code == 503
        assert exc.value.code == "GOOGLE_LOGIN_NOT_CONFIGURED"

    def test_두_번째_플랫폼_ID_도_허용된다(self):
        """안드로이드·iOS·웹이 각각 다른 클라이언트 ID 를 받는다."""
        ios = "ios-client.apps.googleusercontent.com"
        v = GoogleIdentityVerifier(
            audiences=[CLIENT_ID, ios], jwk_client=FakeJwkClient()
        )
        assert v.verify(make_id_token(audience=ios)).subject == "1234567890"
