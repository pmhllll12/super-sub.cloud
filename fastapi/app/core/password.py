"""비밀번호 해싱. bcrypt 를 직접 부른다.

**passlib 을 쓰지 않는다.** passlib 이 bcrypt 백엔드의 버전을 읽는 방식이 bcrypt
4.x 이후와 어긋나 경고·오작동을 내는 사례가 있었다. 우리가 쓰는 기능은 해시 생성과
검증 둘뿐이라 얇은 래퍼로 충분하다.

⚠️ **bcrypt 는 72바이트를 넘는 입력을 조용히 잘라낸다.** 그대로 두면 아주 긴
비밀번호에서 앞 72바이트만 같으면 통과한다. 여기서 명시적으로 거른다.
"""

from __future__ import annotations

import bcrypt

# bcrypt 알고리즘의 한계값. UTF-8 인코딩 후 기준이라 한글은 글자당 3바이트다.
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """bcrypt 가 다룰 수 있는 길이를 넘었다."""


def _encoded(plain: str) -> bytes:
    raw = plain.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"비밀번호가 너무 깁니다(UTF-8 {MAX_PASSWORD_BYTES}바이트 이하)."
        )
    return raw


def hash_password(plain: str) -> str:
    """저장할 해시 문자열을 만든다. 솔트는 bcrypt 가 알아서 넣는다."""
    return bcrypt.hashpw(_encoded(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """맞으면 True. **틀린 이유는 알려주지 않는다.**

    해시 형식이 깨져 있어도 예외를 밖으로 내지 않는다 — 로그인 경로에서 예외가
    나면 "그 계정은 존재한다"는 정보가 새어 나간다.
    """
    try:
        return bcrypt.checkpw(_encoded(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
